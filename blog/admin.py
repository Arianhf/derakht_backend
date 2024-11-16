from wagtail_modeladmin.options import ModelAdmin, modeladmin_register

from stories.models import StoryCollection
from .models import BlogPost


class BlogPostAdmin(ModelAdmin):
    model = BlogPost
    menu_label = 'Blog Posts'
    menu_icon = 'doc-full'
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ('title', 'date', 'author')
    search_fields = ('title', 'body')


class StoryCollectionAdmin(ModelAdmin):
    model = StoryCollection
    menu_label = 'Story Collections'
    menu_icon = 'folder-open-inverse'
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ('title', 'created_at', 'updated_at')
    search_fields = ('title', 'description')


modeladmin_register(BlogPostAdmin)
modeladmin_register(StoryCollectionAdmin)