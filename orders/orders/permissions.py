from rest_framework import permissions
from rest_framework.permissions import BasePermission


# class IsOwnerOrReadOnly(BasePermission):
#     def has_object_permission(self, request, view, obj):
#
#         # if request.method in permissions.SAFE_METHODS:
#         #     return True
#
#         # return request.user == obj.creator
#         return False
#
#     def has_permission(self, request, view):
#         print(dir(view))
#         print(view.request.user, request.user)
#         return True
