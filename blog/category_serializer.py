from rest_framework import serializers
from blog.models import BlogCategory


class BlogCategorySerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()

    class Meta:
        model = BlogCategory
        fields = ["id", "name", "slug", "description", "icon", "post_count"]
        read_only_fields = fields

    def get_post_count(self, obj):
        """Return the number of blog posts in this category"""
        # With ParentalManyToManyField, the reverse relation is determined by the related_name
        # If no related_name was specified in the model, we use lowercase model name + 's'
        return (
            obj.blogposts.count()
            if hasattr(obj, "blogposts")
            else obj.blogpost_set.count()
        )

    def get_icon(self, obj):
        """Return the icon URL if it exists"""
        if obj.icon:
            return obj.icon.get_rendition("original").url
        return None
