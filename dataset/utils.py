import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

def load_dataset(file_path):
    try:
        df = pd.read_csv(file_path)
        required_columns = {'movie_id', 'title', 'cast', 'crew'}
        if not required_columns.issubset(df.columns):
            raise ValueError(f"Dataset is missing one or more required columns: {required_columns}")
        return df
    except Exception as e:
        raise ValueError(f"Error loading dataset: {e}")


def get_movie_recommendations(movie_title, dataset_path, top_n=5):
    """
    Get movie recommendations based on cosine similarity.
    """
    # Load the dataset
    df = load_dataset(dataset_path)
    
    # Check if the necessary columns exist
    if 'title' not in df.columns or 'description' not in df.columns:
        raise ValueError("Dataset must contain 'title' and 'description' columns.")
    
    # Fill NaN descriptions with empty strings
    df['description'] = df['description'].fillna('')
    
    # Create a TF-IDF vectorizer and compute the matrix
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(df['description'])
    
    # Compute cosine similarity matrix
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
    
    # Get the index of the movie that matches the title
    indices = pd.Series(df.index, index=df['title']).drop_duplicates()
    
    if movie_title not in indices:
        raise ValueError(f"Movie '{movie_title}' not found in the dataset.")
    
    idx = indices[movie_title]
    
    # Get pairwise similarity scores and sort them
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    
    # Get the top N similar movies
    sim_scores = sim_scores[1:top_n+1]
    movie_indices = [i[0] for i in sim_scores]
    
    # Return the titles and similarity scores
    return df.iloc[movie_indices][['title', 'description']].to_dict('records')
