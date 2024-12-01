
from django.urls import path
from .views import *

urlpatterns = [
    path('datasets/', DatasetCreateView.as_view(), name='dataset-create'),
    path('movies/', MovieRecommendationView.as_view(), name='movie-recommendations'),
    path('suggestion/', MovieSuggestView.as_view(), name='movie-recommendations'),
    path('dataset/', MovieListView.as_view(), name='list-movies-from-datasets'),
]
