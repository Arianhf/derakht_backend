from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Story, StoryTemplate, StoryCollection, StoryPart
from .serializers import (
    StorySerializer, StoryTemplateSerializer,
    StoryPartSerializer, StoryCollectionSerializer
)


class StoryTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StoryTemplate.objects.all()
    serializer_class = StoryTemplateSerializer

    def get_queryset(self):
        queryset = StoryTemplate.objects.all()
        activity_type = self.request.query_params.get('activity_type', None)
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        return queryset


class StoryViewSet(viewsets.ModelViewSet):
    queryset = Story.objects.all()
    serializer_class = StorySerializer

    @action(detail=True, methods=['post'])
    def add_part(self, request, pk=None):
        story = self.get_object()
        serializer = StoryPartSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(story=story)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def create_from_template(self, request, pk=None):
        try:
            template = StoryTemplate.objects.get(pk=pk)
        except StoryTemplate.DoesNotExist:
            return Response(
                {'error': 'Template not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        story = Story.objects.create(
            title=f"New Story based on {template.title}",
            author=request.data.get('author', 'Guest'),
            activity_type=template.activity_type,
            is_template=False
        )

        for template_part in template.template_parts.all():
            StoryPart.objects.create(
                story=story,
                position=template_part.position,
                text=template_part.prompt_text,
                illustration=template_part.illustration
            )

        serializer = self.get_serializer(story)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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