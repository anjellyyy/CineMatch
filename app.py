import pickle
import streamlit as st
import requests
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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
    except:
        return None


# ---------------- Load Files ---------------- #
movies = pickle.load(open("movies.pkl", "rb"))

# ❌ REMOVED similarity.pkl (this was breaking deployment)

# ---------------- Build similarity again (SAFE VERSION) ---------------- #
cv = CountVectorizer(max_features=5000, stop_words='english')
vectors = cv.fit_transform(movies['tags'].values.astype(str)).toarray()
similarity = cosine_similarity(vectors)


# ---------------- Recommendation Function ---------------- #
def recommend(movie):
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


# ---------------- Streamlit UI (UNCHANGED) ---------------- #
st.set_page_config(page_title="CineMatch", page_icon="🎬", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"],
    .block-container, .main {
        background-color: #141414 !important;
    }
    section, main { background-color: #141414 !important; }
    *, *::before, *::after { color: #ffffff !important; }
    h1 { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }

    [data-testid="stSelectbox"] > div > div {
        background-color: #2a2a2a !important;
        border: 1px solid #555 !important;
        border-radius: 8px !important;
    }

    [data-testid="stButton"] > button {
        background-color: #e50914 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 30px !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        margin-top: 8px !important;
    }
    [data-testid="stButton"] > button:hover {
        background-color: #b20710 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div style="text-align:center; padding: 0 0 0.5rem 0; margin-top: -3rem;">
        <h1 style="font-size:3.5rem; font-weight:900; letter-spacing:3px; margin-bottom:0;">
        🎬 CineMatch
        </h1>
        <p style="color:#aaaaaa; font-size:1.1rem; margin-top:0.3rem;">
        Find movies similar to what you love 🍿
        </p>
    </div>
""", unsafe_allow_html=True)

st.divider()

selected_movie = st.selectbox("🔍 Choose a movie", movies["title"].values)

if st.button("Get Recommendations"):
    with st.spinner("Finding movies you'll love..."):
        names, posters = recommend(selected_movie)

    st.subheader("✨ Recommended For You")

    cols = st.columns(5)

    for i in range(5):
        with cols[i]:
            if posters[i]:
                st.image(posters[i])
            st.write(names[i])