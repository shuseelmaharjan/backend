
from django.urls import path
from .views import *

urlpatterns = [
    path('datasets/', DatasetCreateView.as_view(), name='dataset-create'),
    path('recommend/', MovieRecommendView.as_view(), name='movie-recommend'),
    path('suggest/', MovieSuggestView.as_view(), name='movie-suggest'),
]
