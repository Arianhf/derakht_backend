from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.images.api.v2.views import ImagesAPIViewSet

from blog.views import BlogPostAPIViewSet, BlogIndexPageAPIViewSet

router = WagtailAPIRouter('blog')

router.register_endpoint('pages', PagesAPIViewSet)
router.register_endpoint('posts', BlogPostAPIViewSet)
router.register_endpoint('index', BlogIndexPageAPIViewSet)
router.register_endpoint('images', ImagesAPIViewSet)
