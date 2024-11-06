from wagtail_modeladmin.options import ModelAdmin, modeladmin_register

from content.models import StoryCollection
from .models import BlogPost

from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin.rich_text.converters.html_to_contentstate import (
    InlineStyleElementHandler,
    BlockElementHandler
)
import wagtail.admin.rich_text.editors.draftail.features as draftail_features

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

@hooks.register("register_rich_text_features")
def register_code_styling(features):
    """Add the <code> to the richtext editor and page."""
    feature_name = "code"
    type_ = "CODE"
    tag = "code"

    control = {
        "type": type_,
        "icon": "code",
        "description": "Code",
    }

    features.register_editor_plugin(
        "draftail",
        feature_name,
        draftail_features.InlineStyleFeature(control)
    )

    db_conversion = {
        "from_database_format": {tag: InlineStyleElementHandler(type_)},
        "to_database_format": {"style_map": {type_: {"element": tag}}}
    }

    features.register_converter_rule("contentstate", feature_name, db_conversion)

    if feature_name not in features.default_features:
        features.default_features.append(feature_name)


@hooks.register("register_rich_text_features")
def register_centertext_feature(features):
    """Creates centered text in our richtext editor and page."""
    feature_name = "center"
    type_ = "CENTERTEXT"
    tag = "div"

    control = {
        "type": type_,
        "icon": "align-center",
        "description": "Center Text",
        "element": "div",
    }

    features.register_editor_plugin(
        "draftail",
        feature_name,
        draftail_features.BlockFeature(control)  # Changed to BlockFeature
    )

    features.register_converter_rule(
        "contentstate",
        feature_name,
        {
            "from_database_format": {
                'div[class="text-center"]': BlockElementHandler(type_)
            },
            "to_database_format": {
                "block_map": {  # Changed to block_map
                    type_: {
                        "element": "div",
                        "props": {
                            "class": "text-center"
                        }
                    }
                }
            }
        }
    )

    if feature_name not in features.default_features:
        features.default_features.append(feature_name)

@hooks.register("register_icons")
def register_icons(icons):
    return icons + ['blog/align-center.svg']