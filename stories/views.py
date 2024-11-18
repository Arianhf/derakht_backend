from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Story, StoryTemplate, StoryCollection, StoryPart, StoryPartTemplate, ImageAsset
from .serializers import (
    StorySerializer, StoryTemplateSerializer,
    StoryPartSerializer, StoryCollectionSerializer,
    StoryPartTemplateSerializer, ImageAssetSerializer
)
from rest_framework.parsers import MultiPartParser, FormParser



class StoryTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StoryTemplate.objects.all()
    serializer_class = StoryTemplateSerializer

    def get_queryset(self):
        queryset = StoryTemplate.objects.all()
        activity_type = self.request.query_params.get('activity_type', None)
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        return queryset

    @action(detail=True, methods=['post'])
    def start_story(self, request, pk=None):
        """Initialize a new story from this template"""
        template = self.get_object()

        # Create a new story without parts
        story = Story.objects.create(
            title=f"Draft: {template.title}",
            author=request.user,
            activity_type=template.activity_type,
            story_template=template
        )

        # Return both story and template details
        return Response({
            'story': StorySerializer(story).data,
            'template_parts': StoryPartTemplateSerializer(
                template.template_parts.all().order_by('position'),
                many=True
            ).data
        }, status=status.HTTP_201_CREATED)


class StoryViewSet(viewsets.ModelViewSet):
    serializer_class = StorySerializer

    def get_queryset(self):
        return Story.objects.filter(author=self.request.user)

    @action(detail=True, methods=['post'])
    def add_part(self, request, pk=None):
        """Add a part to the story"""
        story = self.get_object()
        story_part_template_id = request.data.get('story_part_template_id')

        try:
            # Get the template part
            story_part_template = StoryPartTemplate.objects.get(
                id=story_part_template_id,
                template=story.story_template
            )
        except StoryPartTemplate.DoesNotExist:
            return Response(
                {'error': 'Invalid story part template ID'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if this position already has a part
        if StoryPart.objects.filter(
                story=story,
                position=story_part_template.position
        ).exists():
            return Response(
                {'error': 'A part at this position already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create serializer with the data
        serializer = StoryPartSerializer(
            data={
                'text': request.data.get('text', ''),
                'illustration_id': request.data.get('illustration_id'),
                'story_part_template': story_part_template.id
            },
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save(
                story=story,
                position=story_part_template.position
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


    @action(detail=True, methods=['post'])
    def finish(self, request, pk=None):
        """Mark the story as finished and set its final title"""
        story = self.get_object()

        # Verify all template parts have corresponding story parts
        template_parts_count = story.story_template.template_parts.count()
        story_parts_count = story.parts.count()

        if story_parts_count < template_parts_count:
            missing_positions = set(
                story.story_template.template_parts.values_list('position', flat=True)
            ) - set(
                story.parts.values_list('position', flat=True)
            )
            return Response({
                'error': 'All story parts must be completed before finishing',
                'missing_positions': list(missing_positions)
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update the title if provided
        title = request.data.get('title')
        if title:
            story.title = title
            story.save()

        return Response(StorySerializer(story).data)


class StoryCollectionViewSet(viewsets.ModelViewSet):
    queryset = StoryCollection.objects.all()
    serializer_class = StoryCollectionSerializer

    @action(detail=True, methods=['post'])
    def add_story(self, request, pk=None):
        collection = self.get_object()
        story_ids = request.data.get('story_ids', [])

        try:
            stories = StoryTemplate.objects.filter(id__in=story_ids)
            collection.stories.add(*stories)
            serializer = self.get_serializer(collection)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def remove_story(self, request, pk=None):
        collection = self.get_object()
        story_ids = request.data.get('story_ids', [])

        try:
            stories = StoryTemplate.objects.filter(id__in=story_ids)
            collection.stories.remove(*stories)
            serializer = self.get_serializer(collection)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )




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
        return Response({
            'id': serializer.instance.id
        }, status=status.HTTP_201_CREATED)