from django.urls import path
from .views import DatasetCreateView

urlpatterns = [
    path('datasets', DatasetCreateView.as_view(), name='dataset-create'),
]
