import copy
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

from .models import (
    Story,
    StoryTemplate,
    StoryCollection,
    StoryPart,
    StoryPartTemplate,
    ImageAsset,
    StoryStatus,
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


class StoryTemplateViewSet(viewsets.ModelViewSet):
    queryset = StoryTemplate.objects.all()
    serializer_class = StoryTemplateSerializer
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
        queryset = StoryTemplate.objects.all()
        activity_type = self.request.query_params.get("activity_type", None)
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        return queryset

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def start_story(self, request, pk=None):
        """Initialize a new story from this template"""
        template = self.get_object()

        # Create a new story without parts
        story = Story.objects.create(
            title=f"Draft: {template.title}",
            author=request.user,
            activity_type=template.activity_type,
            story_template=template,
            orientation=template.orientation,
            size=template.size,
        )

        # Create story parts with deep copied canvas data from template
        for story_part_template in template.template_parts.all():
            # Deep copy canvas JSON data from template to user instance
            canvas_text_data = copy.deepcopy(story_part_template.canvas_text_template) if story_part_template.canvas_text_template else None
            canvas_illustration_data = copy.deepcopy(story_part_template.canvas_illustration_template) if story_part_template.canvas_illustration_template else None

            StoryPart.objects.create(
                story=story,
                position=story_part_template.position,
                story_part_template=story_part_template,
                canvas_text_data=canvas_text_data,
                canvas_illustration_data=canvas_illustration_data,
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
        if self.action == 'retrieve':
            # Allow access to completed stories from anyone, plus user's own stories
            if self.request.user.is_authenticated:
                # Authenticated users can see their own stories (all statuses) + completed stories from others
                return Story.objects.filter(
                    models.Q(author=self.request.user) | models.Q(status=StoryStatus.COMPLETED)
                ).distinct()
            else:
                # Anonymous users can only see completed stories
                return Story.objects.filter(status=StoryStatus.COMPLETED)

        # For list, create, update, delete: only user's own stories
        return Story.objects.filter(author=self.request.user)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    @method_decorator(csrf_exempt)
    def upload_cover(self, request, pk=None):
        """API endpoint to upload cover image for a story"""
        story = self.get_object()

        if "cover_image" not in request.FILES:
            return Response(
                {"error": "No cover image provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        story.cover_image = request.FILES["cover_image"]
        story.save()

        return Response(StorySerializer(story).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    @method_decorator(csrf_exempt)
    def set_config(self, request, pk=None):
        """API endpoint to set story configuration (colors, fonts, etc.)"""
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
            return Response(
                {"error": e.message_dict},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    @method_decorator(csrf_exempt)
    def add_part(self, request, pk=None):
        """Update a story part with canvas data"""
        story = self.get_object()
        story_part_template_id = request.data.get("story_part_template_id")

        try:
            # Get the template part
            story_part_template = StoryPartTemplate.objects.get(
                id=story_part_template_id, template=story.story_template
            )
        except StoryPartTemplate.DoesNotExist:
            return Response(
                {"error": "Invalid story part template ID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if this position already has a part
        if not StoryPart.objects.filter(
            story=story, story_part_template=story_part_template
        ).exists():
            return Response(
                {"error": "Story part doesn't exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        story_part = StoryPart.objects.get(
            story=story, story_part_template=story_part_template
        )

        # Update canvas data for both text and illustration
        if "canvas_text_data" in request.data:
            story_part.canvas_text_data = request.data.get("canvas_text_data")

        if "canvas_illustration_data" in request.data:
            story_part.canvas_illustration_data = request.data.get("canvas_illustration_data")

        story_part.save()
        serializer = StoryPartSerializer(instance=story_part)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="title")
    @method_decorator(csrf_exempt)
    def update_title(self, request, pk=None):
        """API endpoint to update story title"""
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
        story = self.get_object()

        title = request.data.get("title")
        if title:
            story.title = title

        # Mark the story as completed
        story.status = StoryStatus.COMPLETED
        story.save()

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
    """API endpoint to upload images to story parts for ILLUSTRATE type stories"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """Upload an image to a story part"""
        serializer = StoryPartImageUploadSerializer(data=request.data)

        if not serializer.is_valid():
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
            return Response(
                {"error": "You don't have permission to modify this story."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Update the story part with the image
        story_part.illustration = image
        story_part.save()

        # Return the updated story part
        return Response(
            StoryPartSerializer(story_part).data,
            status=status.HTTP_200_OK
        )
