from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class CSRFExemptMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Exempt views from CSRF protection if they match any of the exempt views
        defined in settings.CSRF_EXEMPT_VIEWS
        """
        # Get exempt views from settings
        exempt_views = getattr(settings, 'CSRF_EXEMPT_VIEWS', [])

        # Get the view class if it exists
        view_class = getattr(view_func, 'cls', None)

        if view_class:
            # Check if the view's class or any of its base classes match exempt views
            for exempt_view in exempt_views:
                if isinstance(exempt_view, str):
                    # If exempt_view is a string, compare with view class name
                    if view_class.__name__ == exempt_view.split('.')[-1]:
                        setattr(request, '_dont_enforce_csrf_checks', True)
                        break
                else:
                    # If exempt_view is a class, check if view_class is a subclass
                    if issubclass(view_class, exempt_view):
                        setattr(request, '_dont_enforce_csrf_checks', True)
                        break
