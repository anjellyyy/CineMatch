import pickle
import streamlit as st
import requests
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------- CONFIG ---------------- #
API_KEY = st.secrets.get("TMDB_API_KEY", "YOUR_API_KEY_HERE")

# ---------------- SESSION (with retries) ---------------- #
def get_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

SESSION = get_session()

# ---------------- FETCH POSTER ---------------- #
def fetch_poster(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"
        response = SESSION.get(url, timeout=10)
        data = response.json()

        poster_path = data.get("poster_path")
        if poster_path:
            return "https://image.tmdb.org/t/p/w500" + poster_path

        return None

    except Exception as e:
        print(f"Poster fetch error for {movie_id}: {e}")
        return None


# ---------------- LOAD DATA ---------------- #
movies = pickle.load(open("movies.pkl", "rb"))

# If you have similarity.pkl, load it. Otherwise fallback mode works.
try:
    similarity = pickle.load(open("similarity.pkl", "rb"))
except Exception:
    similarity = None


# ---------------- RECOMMENDER ---------------- #
def recommend(movie):
    try:
        movie_index = movies[movies["title"] == movie].index[0]

        # -------- FALLBACK MODE -------- #
        if similarity is None:
            sample = movies.sample(5)

            ids_and_names = list(zip(sample["movie_id"], sample["title"]))

        # -------- ML MODE -------- #
        else:
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

        # Fetch posters in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            posters = list(executor.map(lambda x: fetch_poster(x[0]), ids_and_names))

        names = [x[1] for x in ids_and_names]

        return names, posters

    except Exception as e:
        st.error("⚠️ Recommendation system error. Try another movie.")
        print(e)
        return [], []


# ---------------- UI CONFIG ---------------- #
st.set_page_config(page_title="CineMatch", page_icon="🎬", layout="wide")

# ---------------- CSS ---------------- #
st.markdown("""
<style>

body, .main {
    background:#141414 !important;
}

/* global text */
p, span, label {
    color:white !important;
}

/* app background */
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
.block-container {
    background:#141414 !important;
}

/* select box */
[data-testid="stSelectbox"] > div > div {
    background:#222 !important;
    border:1px solid #444 !important;
    border-radius:10px !important;
    color:white !important;
}

/* dropdown */
div[data-baseweb="popover"] {
    background:#1b1b1b !important;
    border:1px solid #333 !important;
}

/* options */
div[data-baseweb="popover"] li {
    background:#1b1b1b !important;
    color:white !important;
}

div[data-baseweb="popover"] li:hover {
    background:#E50914 !important;
}

/* button */
[data-testid="stButton"] > button {
    background:#E50914 !important;
    color:white !important;
    border:none !important;
    border-radius:8px !important;
    font-weight:700 !important;
}

[data-testid="stButton"] > button:hover {
    background:#B20710 !important;
    transform:scale(1.03);
}

/* images */
[data-testid="stImage"] img {
    border-radius:12px;
    transition:0.25s;
}

[data-testid="stImage"] img:hover {
    transform:scale(1.03);
}

</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ---------------- #
st.markdown("""
<div style="text-align:center; padding-bottom:1rem;">
    <h1 style="font-size:3.2rem; font-weight:900;">🎬 CineMatch</h1>
    <p style="color:#aaa;">Find movies similar to what you love 🍿</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ---------------- INPUT ---------------- #
selected_movie = st.selectbox("🔍 Choose a movie", movies["title"].values)

# ---------------- BUTTON ---------------- #
if st.button("Get Recommendations"):

    with st.spinner("Finding movies you'll love..."):
        names, posters = recommend(selected_movie)

    st.markdown("### ✨ Recommended For You")

    # safe loop (prevents index crash)
    max_items = min(5, len(names), len(posters))
    cols = st.columns(5, gap="medium")

    for i in range(max_items):
        with cols[i]:

            if posters[i]:
                st.image(posters[i], use_container_width=True)
            else:
                st.markdown("""
                <div style="background:#2a2a2a; border-radius:10px;
                height:280px; display:flex; align-items:center;
                justify-content:center; color:#888;">
                🎞️ No Poster Available
                </div>
                """, unsafe_allow_html=True)

            st.markdown(
                f"<p style='text-align:center; font-weight:600'>{names[i]}</p>",
                unsafe_allow_html=True
            )