from rest_framework import serializers
from wagtail.api.v2.serializers import PageSerializer
from wagtail.rich_text import expand_db_html

from blog.models import BlogPost


class BlogPostSerializer(PageSerializer):
    class Meta:
        model = BlogPost

    subtitle = serializers.CharField()
    intro = serializers.CharField()
    body = serializers.SerializerMethodField()
    date = serializers.DateField()
    tags = serializers.SerializerMethodField()
    header_image = serializers.SerializerMethodField()
    jalali_date = serializers.SerializerMethodField()
    alternative_titles = serializers.SerializerMethodField()
    schema_markup = serializers.SerializerMethodField()

    def get_body(self, obj):
        # Convert internal Wagtail rich text format to HTML
        return expand_db_html(obj.body)

    def get_tags(self, obj):
        return [{'name': tag.name, 'slug': tag.slug} for tag in obj.tags.all()]

    def get_header_image(self, obj):
        if obj.header_image:
            return {
                'id': obj.header_image.id,
                'title': obj.header_image.title,
                'url': obj.header_image.get_rendition('original').url,
            }
        return None

    def get_jalali_date(self, obj):
        jalali_date = getattr(obj, 'jalali_date', None)
        return str(jalali_date) if jalali_date else None

    def get_alternative_titles(self, obj):
        return obj.alternative_titles

    def get_schema_markup(self, obj):
        return obj.get_schema_markup()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['jalali_date'] = self.get_jalali_date(instance)
        data['schema_markup'] = self.get_schema_markup(instance)
        return data
