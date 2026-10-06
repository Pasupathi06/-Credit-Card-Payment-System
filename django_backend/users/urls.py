from django.urls import path

from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    AdminUserListView,
    AdminUserUpdateView,
    AdminUserDeleteView,
)


urlpatterns = [
    path(
        "register/",
        RegisterView.as_view(),
        name="register",
    ),

    path(
        "login/",
        LoginView.as_view(),
        name="login",
    ),

    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),

    path(
        "admin/users/",
        AdminUserListView.as_view(),
        name="admin-user-list",
    ),

    path(
        "admin/users/<int:pk>/",
        AdminUserUpdateView.as_view(),
        name="admin-user-update",
    ),

    path(
        "admin/users/<int:pk>/delete/",
        AdminUserDeleteView.as_view(),
        name="admin-user-delete",
    ),
]