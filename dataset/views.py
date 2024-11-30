from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Dataset
from .serializers import *
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer


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


class MovieRecommendView(APIView):
    def get(self, request, *args, **kwargs):
        """
        API to recommend movies based on content similarity (using title, cast, crew).
        """
        # Extract the query parameter for the movie title
        movie_title = request.query_params.get('title', None)

        # Validate that the movie title is provided
        if not movie_title:
            return Response({"error": "Movie title is required as a query parameter."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch all datasets from the database
            datasets = Dataset.objects.all()
            recommendations = []

            for dataset in datasets:
                dataset_path = dataset.file.path  # Get the full file path for each dataset
                try:
                    # Generate recommendations for the current dataset
                    recs = self.get_movie_recommendations(movie_title, dataset_path)
                    if recs:
                        recommendations.extend(recs)
                except Exception as e:
                    continue  # Skip datasets that may cause errors but continue with the rest

            # Return unique recommendations, if any
            if recommendations:
                return Response({"recommendations": list(set(recommendations))}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "No recommendations found."}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    def get_movie_recommendations(self, movie_title, dataset_path):
        """
        Generate movie recommendations based on the cosine similarity of the movie title, cast, and crew.
        """
        try:
            # Load the dataset (assuming it's a CSV file)
            df = pd.read_csv(dataset_path)
            if 'title' not in df.columns:
                raise ValueError("Dataset must contain a 'title' column.")
            
            # Combine title, cast, and crew into a single string for each movie
            df['content'] = df['title'] + ' ' + df['cast'].fillna('') + ' ' + df['crew'].fillna('')

            # Use TF-IDF Vectorizer to convert text to numeric vectors
            tfidf_vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = tfidf_vectorizer.fit_transform(df['content'])

            # Check if the movie title exists in the dataset
            if movie_title.lower() not in df['title'].str.lower().values:
                return []

            # Compute cosine similarity between the provided movie title and the entire dataset
            movie_idx = df[df['title'].str.lower() == movie_title.lower()].index[0]
            cosine_sim = cosine_similarity(tfidf_matrix[movie_idx], tfidf_matrix).flatten()

            # Get the indices of the most similar movies
            similar_indices = cosine_sim.argsort()[-6:-1][::-1]  # Top 5 similar movies

            # Return the movie titles
            recommendations = df['title'].iloc[similar_indices].tolist()
            return recommendations

        except Exception as e:
            raise ValueError(f"Error during recommendation generation: {str(e)}")


class MovieSuggestView(APIView):
    def get(self, request, *args, **kwargs):
        """
        Suggest movie titles based on partial input.
        """
        query = request.query_params.get('query', '').lower()

        # Validate that the query is provided
        if not query:
            return Response({"error": "Query is required as a parameter."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch all datasets from the database
            datasets = Dataset.objects.all()
            suggestions = []

            for dataset in datasets:
                dataset_path = dataset.file.path
                df = pd.read_csv(dataset_path)

                if 'title' not in df.columns:
                    continue  # Skip datasets that do not contain a 'title' column
                
                # Suggest titles that match the query
                matching_titles = df['title'][df['title'].str.contains(query, case=False)].head(10).tolist()
                suggestions.extend(matching_titles)

            # Return unique suggestions, if any
            if suggestions:
                return Response({"suggestions": list(set(suggestions))}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "No suggestions found."}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
