from django.templatetags.static import static

from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin.rich_text.converters.html_to_contentstate import (
    InlineStyleElementHandler,
    BlockElementHandler
)
import wagtail.admin.rich_text.editors.draftail.features as draftail_features


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
        "style": {
            "display": "block",
            "text-align": "center",
        }
    }

    features.register_editor_plugin(
        "draftail", feature_name, draftail_features.InlineStyleFeature(control)
    )
    db_conversion = {
        "from_database_format": {tag: InlineStyleElementHandler(type_)},
        "to_database_format": {
            "style_map": {
                type_: {
                    "element": tag,
                    "props": {
                        "class": "text-center"
                    }
                }
            }
        }
    }

    features.register_converter_rule("contentstate", feature_name, db_conversion)

    if feature_name not in features.default_features:
        features.default_features.append(feature_name)

@hooks.register("register_icons")
def register_icons(icons):
    return icons + [
        'blog/align-center.svg',
        'blog/font.svg',
        'blog/align-left.svg'
    ]

@hooks.register("register_rich_text_features")
def register_text_align_left(features):
    """Add left align feature to the editor."""
    feature_name = "text-align-left"
    type_ = "TEXTALIGNLEFT"
    tag = "div"

    control = {
        "type": type_,
        "icon": "align-left",
        "description": "Left align",
        "style": {
            "display": "block",
            "text-align": "left",
        }
    }

    features.register_editor_plugin(
        "draftail", feature_name, draftail_features.InlineStyleFeature(control)
    )

    db_conversion = {
        "from_database_format": {tag: InlineStyleElementHandler(type_)},
        "to_database_format": {
            "style_map": {
                type_: {
                    "element": tag,
                    "props": {
                        "class": "text-end"
                    }
                }
            }
        }
    }

    features.register_converter_rule("contentstate", feature_name, db_conversion)

    if feature_name not in features.default_features:
        features.default_features.append(feature_name)


@hooks.register("register_rich_text_features")
def register_small_text(features):
    """Add small text feature to the editor."""
    feature_name = "small-text"
    type_ = "SMALLTEXT"
    tag = "span"

    control = {
        "type": type_,
        "icon": "minus",
        "description": "Small Text",
        "style": {
            "font-size": "1rem"
        }
    }

    features.register_editor_plugin(
        "draftail", feature_name, draftail_features.InlineStyleFeature(control)
    )

    db_conversion = {
        "from_database_format": {tag: InlineStyleElementHandler(type_)},
        "to_database_format": {
            "style_map": {
                type_: {
                    "element": tag,
                    "props": {
                        "style": "font-size: 1rem"
                    }
                }
            }
        }
    }

    features.register_converter_rule("contentstate", feature_name, db_conversion)

    if feature_name not in features.default_features:
        features.default_features.append(feature_name)


@hooks.register("register_rich_text_features")
def register_normal_text(features):
    """Add normal text feature to the editor."""
    feature_name = "normal-text"
    type_ = "NORMALTEXT"
    tag = "span"

    control = {
        "type": type_,
        "icon": "font",
        "description": "Normal Text",
        "style": {
            "font-size": "1.1rem"
        }
    }

    features.register_editor_plugin(
        "draftail", feature_name, draftail_features.InlineStyleFeature(control)
    )

    db_conversion = {
        "from_database_format": {tag: InlineStyleElementHandler(type_)},
        "to_database_format": {
            "style_map": {
                type_: {
                    "element": tag,
                    "props": {
                        "style": "font-size: 1.1rem"
                    }
                }
            }
        }
    }

    features.register_converter_rule("contentstate", feature_name, db_conversion)

    if feature_name not in features.default_features:
        features.default_features.append(feature_name)


@hooks.register("register_rich_text_features")
def register_large_text(features):
    """Add large text feature to the editor."""
    feature_name = "large-text"
    type_ = "LARGETEXT"
    tag = "span"

    control = {
        "type": type_,
        "icon": "plus",
        "description": "Large Text",
        "style": {
            "font-size": "1.2rem"
        }
    }

    features.register_editor_plugin(
        "draftail", feature_name, draftail_features.InlineStyleFeature(control)
    )

    db_conversion = {
        "from_database_format": {tag: InlineStyleElementHandler(type_)},
        "to_database_format": {
            "style_map": {
                type_: {
                    "element": tag,
                    "props": {
                        "style": "font-size: 1.2rem"
                    }
                }
            }
        }
    }

    features.register_converter_rule("contentstate", feature_name, db_conversion)

    if feature_name not in features.default_features:
        features.default_features.append(feature_name)

@hooks.register("insert_global_admin_css", order=100)
def global_admin_css():
    """Add /static/css/custom.css to the admin."""
    return format_html(
        '<link rel="stylesheet" href="{}">',
        static("css/custom.css")
    )