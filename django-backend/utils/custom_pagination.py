from math import ceil
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomPagination(PageNumberPagination):
    page_size = 10  # Default page size
    page_size_query_param = 'page_size'  # Allow client to set page size with a query parameter
    max_page_size = 500  # Maximum allowed page size

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request)
        total_count = self.page.paginator.count
        total_pages = ceil(total_count / page_size)

        return Response({
            'total_count': total_count,
            'page_size': page_size,  # Use the current page size from the request
            'total_pages': total_pages,  # Add total pages to the response
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
