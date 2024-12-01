from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Dataset
from .serializers import *
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import csv
import requests
import json

class DatasetCreateView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = DatasetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, *args, **kwargs):
        datasets = Dataset.objects.all()
        serializer = DatasetSerializer(datasets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MovieRecommendationView(APIView):
    def get(self, request, *args, **kwargs):
        # Ensure a movie ID is passed in the query params
        movie_id = request.query_params.get('movie_id')
        if not movie_id:
            return Response({"error": "movie_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the dataset file
        dataset_obj = Dataset.objects.first()
        if not dataset_obj:
            return Response({"error": "Dataset not found."}, status=status.HTTP_404_NOT_FOUND)

        # Load the dataset CSV
        file_path = dataset_obj.file.path
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return Response({"error": f"Failed to load dataset: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Validate required columns
        required_columns = {'movie_id', 'title', 'cast', 'crew'}
        if not required_columns.issubset(df.columns):
            return Response({"error": f"Dataset must contain columns: {required_columns}"}, status=status.HTTP_400_BAD_REQUEST)

        # Combine relevant fields into a single text column
        df['combined'] = df['title'].fillna('') + ' ' + df['cast'].fillna('') + ' ' + df['crew'].fillna('')

        # Check if movie_id exists in the dataset
        if movie_id not in df['movie_id'].astype(str).values:
            return Response({"error": f"Movie ID {movie_id} not found in the dataset."}, status=status.HTTP_404_NOT_FOUND)

        # Vectorize the combined text
        tfidf = TfidfVectorizer(stop_words='english')
        tfidf_matrix = tfidf.fit_transform(df['combined'])

        # Calculate cosine similarity
        cosine_sim = cosine_similarity(tfidf_matrix)

        # Find the index of the given movie_id
        movie_idx = df[df['movie_id'] == int(movie_id)].index[0]

        # Get similarity scores for the given movie
        sim_scores = list(enumerate(cosine_sim[movie_idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

        # Retrieve top recommendations (excluding the movie itself)
        top_recommendations = sim_scores[1:6]  # Top 5 similar movies
        recommendations = []
        for idx, score in top_recommendations:
            recommendations.append({
                "movie_id": df.iloc[idx]['movie_id'],
                "title": df.iloc[idx]['title'],
                "similarity_score": score
            })

        # Return recommendations
        return Response({"movie_id": movie_id, "recommendations": recommendations}, status=status.HTTP_200_OK)

class MovieListView(APIView):
    def get(self, request):
        """
        Handle GET requests to fetch movie data (movie_id, title) from all datasets.
        """
        all_movies = []

        # Get all datasets from the database
        datasets = Dataset.objects.all()

        # Iterate through all datasets and extract movie data
        for dataset in datasets:
            try:
                # Open the CSV file associated with the current dataset
                with dataset.file.open('r') as csvfile:
                    reader = csv.DictReader(csvfile)

                    # Iterate through each row in the CSV file
                    for row in reader:
                        # Get movie_id and title for each row in the CSV
                        movie_id = row.get("movie_id")
                        title = row.get("title")

                        # Only add to the list if both movie_id and title exist
                        if movie_id and title:
                            all_movies.append({
                                "movie_id": movie_id,
                                "title": title
                            })

            except Exception as e:
                # Return an error response if there's an issue with reading the CSV file
                return Response({
                    "error": "Failed to read the dataset file.",
                    "details": str(e)
                }, status=400)

        # Return the list of all movies from all datasets
        return Response(all_movies)

def fetch_poster(movie_id):
    url = "https://api.themoviedb.org/3/movie/{}?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US".format(movie_id)
    try:
        data = requests.get(url)
        data.raise_for_status()
        data = data.json()
        poster_path = data.get('poster_path')
        if poster_path:
            return "https://image.tmdb.org/t/p/w500/" + poster_path
        else:
            return None
    except requests.exceptions.RequestException:
        return None

class MovieSuggestView(APIView):
    def get(self, request, *args, **kwargs):
        # Ensure a movie ID is passed in the query params
        movie_id = request.query_params.get('movie_id')
        if not movie_id:
            return Response({"error": "movie_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the dataset file
        dataset_obj = Dataset.objects.first()
        if not dataset_obj:
            return Response({"error": "Dataset not found."}, status=status.HTTP_404_NOT_FOUND)

        # Load the dataset CSV
        file_path = dataset_obj.file.path
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return Response({"error": f"Failed to load dataset: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Validate required columns
        required_columns = {'movie_id', 'title', 'cast', 'crew'}
        if not required_columns.issubset(df.columns):
            return Response({"error": f"Dataset must contain columns: {required_columns}"}, status=status.HTTP_400_BAD_REQUEST)

        # Function to extract cast names from the nested 'cast' column
        def extract_cast_names(cast_column):
            try:
                cast_data = json.loads(cast_column)  # assuming the 'cast' column is a JSON string
                return ' '.join([actor['name'] for actor in cast_data if 'name' in actor])
            except (json.JSONDecodeError, TypeError):
                return ''

        # Function to extract crew roles from the nested 'crew' column
        def extract_crew_roles(crew_column):
            try:
                crew_data = json.loads(crew_column)  # assuming the 'crew' column is a JSON string
                return ' '.join([crew_member['name'] for crew_member in crew_data if 'name' in crew_member])
            except (json.JSONDecodeError, TypeError):
                return ''

        # Apply the extraction functions to the cast and crew columns
        df['cast_names'] = df['cast'].apply(extract_cast_names)
        df['crew_roles'] = df['crew'].apply(extract_crew_roles)

        # Combine relevant fields into a single text column
        df['combined'] = df['title'].fillna('') + ' ' + df['cast_names'].fillna('') + ' ' + df['crew_roles'].fillna('')

        # Check if movie_id exists in the dataset
        if int(movie_id) not in df['movie_id'].values:
            return Response({"error": f"Movie ID {movie_id} not found in the dataset."}, status=status.HTTP_404_NOT_FOUND)

        # Vectorize the combined text
        tfidf = TfidfVectorizer(stop_words='english')
        tfidf_matrix = tfidf.fit_transform(df['combined'])

        # Calculate cosine similarity
        cosine_sim = cosine_similarity(tfidf_matrix)

        # Find the index of the given movie_id
        movie_idx = df[df['movie_id'] == int(movie_id)].index[0]

        # Get similarity scores for the given movie
        sim_scores = list(enumerate(cosine_sim[movie_idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

        # Retrieve top recommendations (excluding the movie itself)
        top_recommendations = sim_scores[1:6]  # Top 5 similar movies
        recommendations = []
        for idx, score in top_recommendations:
            recommended_movie = df.iloc[idx]
            # Fetch poster (add your fetch_poster logic here)
            poster_url = fetch_poster(recommended_movie['movie_id'])

            # Add the recommendation to the list
            recommendations.append({
                "movie_id": recommended_movie['movie_id'],
                "title": recommended_movie['title'],
                "poster_url": poster_url,
                "similarity_score": score
            })

        # Return recommendations
        return Response({"movie_id": movie_id, "recommendations": recommendations}, status=status.HTTP_200_OK)