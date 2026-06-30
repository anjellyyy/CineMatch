import pickle
import streamlit as st
import requests
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer

API_KEY = "8935f4abb2ac21f7798ac858092add50"

# ---------------- Session with retries ---------------- #
def get_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

SESSION = get_session()

# ---------------- Fetch Poster ---------------- #
def fetch_poster(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"
    try:
        response = SESSION.get(url, timeout=10, verify=False)
        data = response.json()
        poster_path = data.get("poster_path")
        if poster_path:
            return "https://image.tmdb.org/t/p/w500" + poster_path
        return None
    except Exception:
        return None


# ---------------- Load Data ---------------- #
movies = pickle.load(open("movies.pkl", "rb"))

# ---------------- Build similarity ON THE FLY ---------------- #
# (NO similarity.pkl needed anymore)

cv = CountVectorizer(max_features=5000, stop_words='english')

# If your dataset uses 'tags' column (common in your notebook)
vectors = cv.fit_transform(movies['tags'].values.astype(str)).toarray()

similarity = cosine_similarity(vectors)


# ---------------- Recommendation Function ---------------- #
def recommend(movie):
    try:
        movie_index = movies[movies['title'] == movie].index[0]

        distances = similarity[movie_index]

        movies_list = sorted(
            list(enumerate(distances)),
            reverse=True,
            key=lambda x: x[1]
        )[1:6]

        ids_and_names = [
            (movies.iloc[i[0]].movie_id, movies.iloc[i[0]].title)
            for i in movies_list
        ]

        with ThreadPoolExecutor(max_workers=5) as executor:
            posters = list(executor.map(lambda x: fetch_poster(x[0]), ids_and_names))

        names = [x[1] for x in ids_and_names]
        return names, posters

    except Exception as e:
        st.error("Recommendation error")
        return [], []


# ---------------- UI ---------------- #
st.set_page_config(page_title="CineMatch", page_icon="🎬", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #141414; }
    *, h1, p { color: white !important; }
    [data-testid="stButton"] > button {
        background-color: #e50914;
        color: white;
        border-radius: 8px;
        padding: 10px 30px;
        font-weight: bold;
    }
    [data-testid="stButton"] > button:hover {
        background-color: #b20710;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎬 CineMatch")

selected_movie = st.selectbox("Choose a movie", movies["title"].values)

if st.button("Get Recommendations"):
    with st.spinner("Finding movies..."):
        names, posters = recommend(selected_movie)

    st.subheader("Recommended Movies")

    cols = st.columns(5)

    for i in range(5):
        with cols[i]:
            if posters[i]:
                st.image(posters[i])
            st.write(names[i])