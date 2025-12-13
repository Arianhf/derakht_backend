from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    """
    Custom pagination class that allows clients to specify page size via query parameter
    while enforcing reasonable limits.
    """
    page_size = 10  # Default page size
    page_size_query_param = 'page_size'  # Allow client to override via ?page_size=X
    max_page_size = 100  # Maximum limit for page size to prevent abuse
