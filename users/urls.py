from django.urls import path
from users.views import *

urlpatterns = [
    path('register', UserCreateAPIView.as_view(), name='user-create'),
    path('role/<int:user_id>', UserRoleAPIView.as_view(), name='user-role'),
    path('login', LoginAPIView.as_view(), name='login'),
    path('logout', LogoutAPIView.as_view(), name='logout'),
    path('username', UsernameAPIView.as_view(), name='username'),
]