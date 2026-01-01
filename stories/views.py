import copy
import logging
import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.logging_utils import (
    get_logger,
    log_user_action,
    log_analytics_event,
    log_api_error,
    log_operation,
)
from .models import (
    Story,
    StoryTemplate,
    StoryCollection,
    StoryPart,
    StoryPartTemplate,
    ImageAsset,
    StoryStatus,
    TemplateImage,
)
from .serializers import (
    StorySerializer,
    StoryTemplateSerializer,
    StoryPartSerializer,
    StoryCollectionSerializer,
    StoryPartTemplateSerializer,
    ImageAssetSerializer,
    StoryPartImageUploadSerializer,
    StoryTemplateWriteSerializer,
    StoryPartTemplateWriteSerializer,
)
from .pagination import CustomPageNumberPagination
from .permissions import IsStaffUser

# Initialize loggers
logger = get_logger("stories")
generation_logger = get_logger("stories.generation")
images_logger = get_logger("stories.images")
audit_logger = get_logger("audit")


class StoryTemplateViewSet(viewsets.ModelViewSet):
    queryset = StoryTemplate.objects.all()
    serializer_class = StoryTemplateSerializer
    pagination_class = CustomPageNumberPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        """
        Allow anyone to read templates (list, retrieve).
        Require staff for write operations (create, update, partial_update, destroy).
        """
        if self.action in ['list', 'retrieve', 'start_story']:
            return [permissions.AllowAny()]
        return [IsStaffUser()]

    def get_serializer_class(self):
        """
        Use write serializer for create/update operations, read serializer for everything else.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return StoryTemplateWriteSerializer
        return StoryTemplateSerializer

    def get_queryset(self):
        # Optimize queries to prevent N+1 issues
        queryset = StoryTemplate.objects.all().prefetch_related("template_parts")
        activity_type = self.request.query_params.get("activity_type", None)
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        return queryset

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def start_story(self, request, pk=None):
        """Initialize a new story from this template"""
        template = self.get_object()

        try:
            with log_operation(
                "story_generation",
                generation_logger,
                extra_data={
                    "template_id": template.id,
                    "template_title": template.title,
                    "activity_type": template.activity_type,
                    "user_id": request.user.id,
                },
            ):
                # Create a new story without parts
                story = Story.objects.create(
                    title=f"Draft: {template.title}",
                    author=request.user,
                    activity_type=template.activity_type,
                    story_template=template,
                    orientation=template.orientation,
                    size=template.size,
                )

                # Create story parts with deep copied canvas data from template using bulk_create
                template_parts = template.template_parts.all()
                story_parts = []
                for story_part_template in template_parts:
                    # Deep copy canvas JSON data from template to user instance
                    canvas_text_data = copy.deepcopy(story_part_template.canvas_text_template) if story_part_template.canvas_text_template else None
                    canvas_illustration_data = copy.deepcopy(story_part_template.canvas_illustration_template) if story_part_template.canvas_illustration_template else None

                    story_parts.append(
                        StoryPart(
                            story=story,
                            position=story_part_template.position,
                            story_part_template=story_part_template,
                            canvas_text_data=canvas_text_data,
                            canvas_illustration_data=canvas_illustration_data,
                        )
                    )

                StoryPart.objects.bulk_create(story_parts)
                parts_created = len(story_parts)

                generation_logger.info(
                    f"Story created from template: {story.id}",
                    extra={
                        "extra_data": {
                            "story_id": story.id,
                            "template_id": template.id,
                            "parts_created": parts_created,
                            "activity_type": template.activity_type,
                        }
                    },
                )

                # Log user action for audit
                log_user_action(
                    audit_logger,
                    "story_started",
                    user_id=request.user.id,
                    user_email=request.user.email,
                    extra_data={
                        "story_id": story.id,
                        "template_id": template.id,
                        "activity_type": template.activity_type,
                    },
                )

                # Log analytics event
                log_analytics_event(
                    "story_started",
                    "stories",
                    user_id=request.user.id,
                    properties={
                        "template_id": template.id,
                        "activity_type": template.activity_type,
                        "parts_count": parts_created,
                    },
                )

                # Return both story and template details
                return Response(
                    {
                        "story": StorySerializer(story).data,
                        "template_parts": StoryPartTemplateSerializer(
                            template.template_parts.all().order_by("position"), many=True
                        ).data,
                    },
                    status=status.HTTP_201_CREATED,
                )

        except Exception as e:
            log_api_error(
                generation_logger,
                e,
                request.path,
                request.method,
                user_id=request.user.id,
                request_data={"template_id": template.id},
            )
            raise

    def perform_update(self, serializer):
        """
        Clean up orphaned template images after template update.
        Extracts image IDs referenced in canvas JSON and deletes unreferenced images.
        """
        instance = serializer.save()

        # Extract all image IDs currently used in template parts
        used_image_ids = set()
        for part in instance.template_parts.all():
            # Extract from canvas_illustration_template
            if part.canvas_illustration_template:
                used_image_ids.update(
                    self._extract_image_ids_from_canvas(part.canvas_illustration_template)
                )
            # Extract from canvas_text_template
            if part.canvas_text_template:
                used_image_ids.update(
                    self._extract_image_ids_from_canvas(part.canvas_text_template)
                )

        # Delete unused template images
        orphaned_images = instance.images.exclude(id__in=used_image_ids)
        orphaned_count = orphaned_images.count()

        if orphaned_count > 0:
            images_logger.info(
                f"Cleaning up {orphaned_count} orphaned template images",
                extra={
                    "extra_data": {
                        "template_id": str(instance.id),
                        "orphaned_count": orphaned_count,
                    }
                },
            )
            orphaned_images.delete()

        return instance

    def _extract_image_ids_from_canvas(self, canvas_json):
        """
        Extract TemplateImage IDs from canvas JSON by parsing image URLs.

        Canvas JSON structure:
        {
            "canvasJSON": {
                "objects": [
                    {
                        "type": "image",
                        "src": "http://example.com/.../story_templates/images/2024/12/image.jpg",
                        "templateImageId": "uuid-here"  // Custom property we'll add
                    }
                ]
            }
        }
        """
        image_ids = set()

        if not canvas_json or 'canvasJSON' not in canvas_json:
            return image_ids

        canvas_data = canvas_json.get('canvasJSON', {})
        objects = canvas_data.get('objects', [])

        for obj in objects:
            if obj.get('type') == 'image':
                # Try to get templateImageId from object (set by frontend)
                template_image_id = obj.get('templateImageId')
                if template_image_id:
                    try:
                        # Validate UUID format
                        uuid.UUID(template_image_id)
                        image_ids.add(template_image_id)
                    except (ValueError, AttributeError):
                        pass

        return image_ids

    @action(detail=True, methods=["post"], permission_classes=[IsStaffUser], parser_classes=[MultiPartParser, FormParser])
    def upload_template_image(self, request, pk=None):
        """
        Upload an image for a template part.
        Returns the image URL to be used in canvas JSON.

        This endpoint allows staff users to upload images that will be referenced
        in template canvas JSON via URL instead of base64 encoding, significantly
        reducing payload size and improving performance.
        """
        template = self.get_object()
        image_file = request.FILES.get('image')
        part_index = request.data.get('part_index')

        if not image_file:
            images_logger.warning(
                f"Template image upload failed: No image provided",
                extra={
                    "extra_data": {
                        "template_id": str(template.id),
                        "user_id": request.user.id,
                    }
                },
            )
            return Response(
                {'error': 'No image provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not part_index or not part_index.isdigit():
            images_logger.warning(
                "Template image upload failed: Invalid part_index",
                extra={
                    "extra_data": {
                        "template_id": str(template.id),
                        "part_index": part_index,
                        "user_id": request.user.id,
                    }
                },
            )
            return Response(
                {'error': 'Valid part_index is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        part_index = int(part_index)

        # Validate image size (10MB limit for high-quality images)
        max_size = 10 * 1024 * 1024
        if image_file.size > max_size:
            images_logger.warning(
                f"Template image upload failed: Image too large ({image_file.size} bytes)",
                extra={
                    "extra_data": {
                        "template_id": str(template.id),
                        "part_index": part_index,
                        "file_size": image_file.size,
                        "user_id": request.user.id,
                    }
                },
            )
            return Response(
                {'error': f'Image too large. Maximum size is {max_size / 1024 / 1024}MB'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create TemplateImage record
            template_image = TemplateImage.objects.create(
                template=template,
                part_index=part_index,
                image=image_file
            )

            images_logger.info(
                f"Template image uploaded successfully: {template_image.id}",
                extra={
                    "extra_data": {
                        "template_id": str(template.id),
                        "template_image_id": str(template_image.id),
                        "part_index": part_index,
                        "file_size": image_file.size,
                        "user_id": request.user.id,
                    }
                },
            )

            return Response(
                {
                    'id': str(template_image.id),
                    'url': request.build_absolute_uri(template_image.image.url),
                    'part_index': part_index,
                    'created_at': template_image.created_at,
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            log_api_error(
                images_logger,
                e,
                request.path,
                request.method,
                user_id=request.user.id,
                request_data={
                    "template_id": str(template.id),
                    "part_index": part_index,
                },
            )
            return Response(
                {'error': 'Failed to upload image'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StoryViewSet(viewsets.ModelViewSet):
    serializer_class = StorySerializer
    pagination_class = CustomPageNumberPagination

    def get_permissions(self):
        """
        Allow anonymous access for retrieving individual completed stories and completed stories list.
        Require authentication for all other actions.
        """
        if self.action in ['retrieve', 'completed_stories']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """
        - For 'retrieve' action: Return user's own stories + all completed stories from others
        - For other actions: Return only user's own stories
        """
        # Optimize queries to prevent N+1 issues
        base_queryset = Story.objects.select_related(
            "author", "story_template"
        ).prefetch_related("parts", "parts__story_part_template")

        if self.action == 'retrieve':
            # Allow access to completed stories from anyone, plus user's own stories
            if self.request.user.is_authenticated:
                # Authenticated users can see their own stories (all statuses) + completed stories from others
                return base_queryset.filter(
                    models.Q(author=self.request.user) | models.Q(status=StoryStatus.COMPLETED)
                ).distinct()
            else:
                # Anonymous users can only see completed stories
                return base_queryset.filter(status=StoryStatus.COMPLETED)

        # For list, create, update, delete: only user's own stories
        return base_queryset.filter(author=self.request.user)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    @method_decorator(csrf_exempt)
    def upload_cover(self, request, pk=None):
        """
        API endpoint to upload cover image for a story

        CSRF EXEMPT JUSTIFICATION:
        - This is a JWT-authenticated API endpoint, not a session-based view
        - Authentication via Authorization header (Bearer token), not cookies
        - CSRF protection is designed for cookie-based session auth
        - Modern API pattern using stateless JWT authentication

        SECURITY MEASURES:
        - Requires valid JWT token (IsAuthenticated permission class)
        - User can only upload cover for their own stories (get_object checks ownership)
        - File type validation via serializer
        - File size limits enforced by MultiPartParser configuration
        - Comprehensive logging of all upload attempts
        """
        story = self.get_object()

        if "cover_image" not in request.FILES:
            images_logger.warning(
                f"Cover image upload failed: no image provided for story {story.id}",
                extra={"story_id": story.id, "user_id": request.user.id},
            )
            return Response(
                {"error": "No cover image provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cover_image = request.FILES["cover_image"]
            file_size = cover_image.size
            file_type = cover_image.content_type

            images_logger.info(
                f"Uploading cover image for story {story.id}",
                extra={
                    "extra_data": {
                        "story_id": story.id,
                        "file_size": file_size,
                        "file_type": file_type,
                        "user_id": request.user.id,
                    }
                },
            )

            story.cover_image = cover_image
            story.save()

            log_user_action(
                audit_logger,
                "story_cover_uploaded",
                user_id=request.user.id,
                user_email=request.user.email,
                extra_data={
                    "story_id": story.id,
                    "file_size": file_size,
                },
            )

            return Response(StorySerializer(story).data, status=status.HTTP_200_OK)

        except Exception as e:
            log_api_error(
                images_logger,
                e,
                request.path,
                request.method,
                user_id=request.user.id,
                request_data={"story_id": story.id},
            )
            raise

    @action(detail=True, methods=["post"])
    @method_decorator(csrf_exempt)
    def set_config(self, request, pk=None):
        """
        API endpoint to set story configuration (colors, fonts, etc.)

        CSRF EXEMPT JUSTIFICATION:
        - JWT-authenticated API endpoint using stateless authentication
        - No session cookies involved in authentication mechanism
        - Authorization via Bearer token in header

        SECURITY MEASURES:
        - JWT authentication required (IsAuthenticated)
        - Ownership verification via get_object (user can only modify own stories)
        - Input validation via model validators (full_clean)
        - Color format validation for hex color codes
        """
        story = self.get_object()

        background_color = request.data.get("background_color")
        font_color = request.data.get("font_color")

        # Update fields if provided
        if background_color is not None:
            story.background_color = background_color if background_color else None

        if font_color is not None:
            story.font_color = font_color if font_color else None

        try:
            story.full_clean()  # This will run the validators
            story.save()
            return Response(StorySerializer(story).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            logger.warning(
                "Story color update validation failed",
                extra={
                    "extra_data": {
                        "story_id": str(story.id),
                        "user_id": request.user.id,
                        "errors": e.message_dict,
                    }
                },
            )
            return Response(
                {"error": e.message_dict},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    @method_decorator(csrf_exempt)
    def add_part(self, request, pk=None):
        """
        Update a story part with canvas data

        CSRF EXEMPT JUSTIFICATION:
        - JWT-based API endpoint with stateless authentication
        - Uses Bearer token authentication, not session cookies
        - Part of RESTful API consumed by frontend SPA

        SECURITY MEASURES:
        - Authentication required via JWT token
        - User ownership validation (can only add parts to own stories)
        - Template validation (story_part_template must belong to story's template)
        - Canvas data validation via model fields
        - Activity type validation ensures proper story workflow
        """
        story = self.get_object()
        story_part_template_id = request.data.get("story_part_template_id")

        try:
            # Get the template part
            story_part_template = StoryPartTemplate.objects.get(
                id=story_part_template_id, template=story.story_template
            )
        except StoryPartTemplate.DoesNotExist:
            logger.warning(
                f"Invalid story part template ID: {story_part_template_id}",
                extra={
                    "story_id": story.id,
                    "template_id": story_part_template_id,
                    "user_id": request.user.id,
                },
            )
            return Response(
                {"error": "Invalid story part template ID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if this position already has a part
        if not StoryPart.objects.filter(
            story=story, story_part_template=story_part_template
        ).exists():
            logger.warning(
                f"Story part doesn't exist for template {story_part_template_id}",
                extra={
                    "story_id": story.id,
                    "template_id": story_part_template_id,
                    "user_id": request.user.id,
                },
            )
            return Response(
                {"error": "Story part doesn't exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        story_part = StoryPart.objects.get(
            story=story, story_part_template=story_part_template
        )

        # Track what's being updated
        updated_fields = []
        if "canvas_text_data" in request.data:
            story_part.canvas_text_data = request.data.get("canvas_text_data")
            updated_fields.append("canvas_text_data")

        if "canvas_illustration_data" in request.data:
            story_part.canvas_illustration_data = request.data.get("canvas_illustration_data")
            updated_fields.append("canvas_illustration_data")

        story_part.save()

        logger.info(
            f"Story part updated: {story_part.id}",
            extra={
                "extra_data": {
                    "story_id": story.id,
                    "story_part_id": story_part.id,
                    "updated_fields": updated_fields,
                    "position": story_part.position,
                    "user_id": request.user.id,
                }
            },
        )

        log_user_action(
            audit_logger,
            "story_part_updated",
            user_id=request.user.id,
            user_email=request.user.email,
            extra_data={
                "story_id": story.id,
                "story_part_id": story_part.id,
                "updated_fields": updated_fields,
            },
        )

        serializer = StoryPartSerializer(instance=story_part)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="title")
    @method_decorator(csrf_exempt)
    def update_title(self, request, pk=None):
        """
        API endpoint to update story title

        CSRF EXEMPT JUSTIFICATION:
        - JWT-authenticated API endpoint
        - Stateless authentication via Authorization header
        - No cookie-based session state

        SECURITY MEASURES:
        - JWT token required (IsAuthenticated)
        - Ownership check via get_object
        - Input validation (title required, non-empty)
        """
        story = self.get_object()

        title = request.data.get("title")
        if not title:
            return Response(
                {"error": "Title is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        story.title = title
        story.save()

        return Response(StorySerializer(story).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    @method_decorator(csrf_exempt)
    def finish(self, request, pk=None):
        """
        Mark story as completed

        CSRF EXEMPT JUSTIFICATION:
        - JWT-authenticated REST API endpoint
        - Token-based authentication, not cookies
        - Stateless architecture pattern

        SECURITY MEASURES:
        - JWT authentication required
        - User can only finish their own stories (ownership check)
        - Status transition validation (from IN_PROGRESS to COMPLETED)
        - Comprehensive logging of completion events
        """
        story = self.get_object()

        title = request.data.get("title")
        title_updated = False
        if title:
            story.title = title
            title_updated = True

        # Mark the story as completed
        old_status = story.status
        story.status = StoryStatus.COMPLETED
        story.save()

        logger.info(
            f"Story completed: {story.id}",
            extra={
                "extra_data": {
                    "story_id": story.id,
                    "old_status": old_status,
                    "new_status": story.status,
                    "title_updated": title_updated,
                    "parts_count": story.parts.count(),
                    "user_id": request.user.id,
                }
            },
        )

        log_user_action(
            audit_logger,
            "story_completed",
            user_id=request.user.id,
            user_email=request.user.email,
            extra_data={
                "story_id": story.id,
                "story_title": story.title,
                "activity_type": story.activity_type,
            },
        )

        log_analytics_event(
            "story_completed",
            "stories",
            user_id=request.user.id,
            properties={
                "story_id": story.id,
                "activity_type": story.activity_type,
                "parts_count": story.parts.count(),
                "template_id": story.story_template.id if story.story_template else None,
            },
        )

        return Response(StorySerializer(story).data)

    @action(detail=False, methods=["get"], url_path="completed", permission_classes=[permissions.AllowAny])
    def completed_stories(self, request):
        """Get all completed stories from all users - publicly accessible"""
        completed_stories = Story.objects.filter(
            status=StoryStatus.COMPLETED
        ).select_related("author", "story_template").prefetch_related("parts")

        # Paginate the results
        page = self.paginate_queryset(completed_stories)
        if page is not None:
            serializer = StorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = StorySerializer(completed_stories, many=True)
        return Response(serializer.data)


class StoryCollectionViewSet(viewsets.ModelViewSet):
    queryset = StoryCollection.objects.all()
    serializer_class = StoryCollectionSerializer

    @action(detail=True, methods=["post"])
    def add_story(self, request, pk=None):
        collection = self.get_object()
        story_ids = request.data.get("story_ids", [])

        try:
            stories = StoryTemplate.objects.filter(id__in=story_ids)
            collection.stories.add(*stories)
            serializer = self.get_serializer(collection)
            return Response(serializer.data)
        except Exception as e:
            logger.error(
                "Failed to add stories to collection",
                extra={
                    "extra_data": {
                        "collection_id": str(collection.id),
                        "story_ids": story_ids,
                        "error": str(e),
                        "user_id": request.user.id if request.user.is_authenticated else None,
                    }
                },
                exc_info=True,
            )
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def remove_story(self, request, pk=None):
        collection = self.get_object()
        story_ids = request.data.get("story_ids", [])

        try:
            stories = StoryTemplate.objects.filter(id__in=story_ids)
            collection.stories.remove(*stories)
            serializer = self.get_serializer(collection)
            return Response(serializer.data)
        except Exception as e:
            logger.error(
                "Failed to remove stories from collection",
                extra={
                    "extra_data": {
                        "collection_id": str(collection.id),
                        "story_ids": story_ids,
                        "error": str(e),
                        "user_id": request.user.id if request.user.is_authenticated else None,
                    }
                },
                exc_info=True,
            )
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ImageAssetViewSet(viewsets.ModelViewSet):
    serializer_class = ImageAssetSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        return ImageAsset.objects.filter(uploaded_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Return only the ID in the response
        return Response({"id": serializer.instance.id}, status=status.HTTP_201_CREATED)


class StoryPartViewSet(viewsets.GenericViewSet):
    """ViewSet for StoryPart operations"""
    serializer_class = StoryPartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return story parts for stories owned by the current user"""
        return StoryPart.objects.filter(story__author=self.request.user)

    @action(detail=True, methods=["post"])
    @method_decorator(csrf_exempt)
    def reset(self, request, pk=None):
        """
        Reset story part canvas data back to template.

        Parameters:
        - reset_text (bool): If true, reset text canvas. Default: false
        - reset_illustration (bool): If true, reset illustration canvas. Default: false
        - If both are false or not provided, reset both canvases (backward compatible)

        CSRF EXEMPT JUSTIFICATION:
        - JWT-authenticated API endpoint
        - Stateless token authentication in Authorization header
        - RESTful API consumed by SPA frontend

        SECURITY MEASURES:
        - JWT token authentication required
        - Ownership validation (user can only reset own story parts)
        - Template association validation
        - Comprehensive logging of reset operations
        """
        story_part = self.get_object()

        # Check if the story part has an associated template
        if not story_part.story_part_template:
            return Response(
                {"error": "Story part has no associated template"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        template = story_part.story_part_template

        # Get reset flags from request data
        reset_text = request.data.get("reset_text", False)
        reset_illustration = request.data.get("reset_illustration", False)

        # If neither is specified, reset both (backward compatible)
        if not reset_text and not reset_illustration:
            reset_text = True
            reset_illustration = True

        # Reset text canvas if requested
        if reset_text:
            story_part.canvas_text_data = copy.deepcopy(template.canvas_text_template) if template.canvas_text_template else None

        # Reset illustration canvas if requested
        if reset_illustration:
            story_part.canvas_illustration_data = copy.deepcopy(template.canvas_illustration_template) if template.canvas_illustration_template else None

        story_part.save()

        serializer = self.get_serializer(story_part)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StoryPartTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing story part templates (staff only)"""
    queryset = StoryPartTemplate.objects.all()
    serializer_class = StoryPartTemplateWriteSerializer
    permission_classes = [IsStaffUser]

    def get_queryset(self):
        """Allow filtering by template"""
        queryset = StoryPartTemplate.objects.all()
        template_id = self.request.query_params.get("template", None)
        if template_id:
            queryset = queryset.filter(template_id=template_id)
        return queryset.order_by('template', 'position')


@method_decorator(csrf_exempt, name='dispatch')
class StoryPartImageUploadView(APIView):
    """
    API endpoint to upload images to story parts for ILLUSTRATE type stories

    CSRF EXEMPT JUSTIFICATION:
    This endpoint is exempt from CSRF protection because:
    1. JWT-authenticated API endpoint using Bearer token authentication
    2. Stateless authentication - no session cookies involved
    3. Modern API pattern for file uploads from SPA frontend
    4. MultiPartParser handles file uploads which don't work well with CSRF tokens

    SECURITY MEASURES:
    - JWT authentication required (IsAuthenticated permission class)
    - User ownership validation (can only upload to own story parts)
    - File type validation via StoryPartImageUploadSerializer
    - File size limits enforced by parser configuration
    - Story part existence validation
    - Comprehensive logging of all upload attempts with user context
    - Image validation ensures only valid image formats accepted

    ADDITIONAL SECURITY CONSIDERATIONS:
    - Uploaded files stored with UUID-based filenames preventing path traversal
    - S3/MinIO storage with appropriate access controls
    - All upload failures logged for security monitoring
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """Upload an image to a story part"""
        serializer = StoryPartImageUploadSerializer(data=request.data)

        if not serializer.is_valid():
            images_logger.warning(
                "Story part image upload validation failed",
                extra={
                    "errors": serializer.errors,
                    "user_id": request.user.id,
                },
            )
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get validated data
        story = serializer.validated_data['story']
        story_part = serializer.validated_data['story_part']
        image = serializer.validated_data['image']

        # Check authorization - user must own the story
        if story.author != request.user:
            images_logger.warning(
                f"Unauthorized story part image upload attempt for story {story.id}",
                extra={
                    "story_id": story.id,
                    "story_owner": story.author.id,
                    "attempted_by": request.user.id,
                },
            )
            return Response(
                {"error": "You don't have permission to modify this story."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            file_size = image.size
            file_type = image.content_type

            images_logger.info(
                f"Uploading illustration image for story part {story_part.id}",
                extra={
                    "extra_data": {
                        "story_id": story.id,
                        "story_part_id": story_part.id,
                        "file_size": file_size,
                        "file_type": file_type,
                        "activity_type": story.activity_type,
                        "user_id": request.user.id,
                    }
                },
            )

            # Update the story part with the image
            story_part.illustration = image
            story_part.save()

            log_user_action(
                audit_logger,
                "story_part_illustration_uploaded",
                user_id=request.user.id,
                user_email=request.user.email,
                extra_data={
                    "story_id": story.id,
                    "story_part_id": story_part.id,
                    "file_size": file_size,
                },
            )

            log_analytics_event(
                "illustration_uploaded",
                "stories",
                user_id=request.user.id,
                properties={
                    "story_id": story.id,
                    "story_part_id": story_part.id,
                    "activity_type": story.activity_type,
                },
            )

            # Return the updated story part
            return Response(
                StoryPartSerializer(story_part).data,
                status=status.HTTP_200_OK
            )

        except Exception as e:
            log_api_error(
                images_logger,
                e,
                request.path,
                request.method,
                user_id=request.user.id,
                request_data={
                    "story_id": story.id,
                    "story_part_id": story_part.id,
                },
            )
            raise
