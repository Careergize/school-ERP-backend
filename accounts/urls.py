from django.urls import path
from .views import LoginAPIView, CurrentUserAPIView, LogoutAPIView, ChangePasswordAPIView, UserListAPIView

app_name = 'accounts'
urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('me/', CurrentUserAPIView.as_view(), name='me'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('password/', ChangePasswordAPIView.as_view(), name='password'),
    path('users/', UserListAPIView.as_view(), name='user-list'),
]
