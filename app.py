import pickle
import os
import gdown
import streamlit as st
import requests
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_KEY = "8935f4abb2ac21f7798ac858092add50"

# ---------------- Download similarity.pkl if not present ---------------- #
SIMILARITY_FILE = "similarity.pkl"
GDRIVE_FILE_ID = "1V0TA7fdNtKmwBaMg_ZHIK3xYl3PPDu9I"

if not os.path.exists(SIMILARITY_FILE):
    with st.spinner("Downloading model files..."):
        gdown.download(
            f"https://drive.google.com/file/d/{GDRIVE_FILE_ID}/view?usp=sharing",
            SIMILARITY_FILE,
            quiet=False,
            fuzzy=True
        )

# ---------------- SESSION WITH RETRIES ---------------- #
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
        print(f"Poster error: {e}")
        return None


# ---------------- LOAD DATA ---------------- #
movies = pickle.load(open("movies.pkl", "rb"))

# IMPORTANT: similarity should exist (either loaded or computed elsewhere)
similarity = pickle.load(open("similarity.pkl", "rb"))


# ---------------- RECOMMEND FUNCTION ---------------- #
def recommend(movie):
    movie_index = movies[movies["title"] == movie].index[0]

    distances = similarity[movie_index]

    movies_list = sorted(
        list(enumerate(distances)),
        reverse=True,
        key=lambda x: x[1]
    )[1:6]

    recommended_movies = []
    recommended_posters = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        for i in movies_list:
            movie_id = movies.iloc[i[0]].movie_id
            recommended_movies.append(movies.iloc[i[0]].title)

            recommended_posters.append(fetch_poster(movie_id))

    return recommended_movies, recommended_posters


# ---------------- STREAMLIT UI ---------------- #

st.set_page_config(page_title="CineMatch", page_icon="🎬", layout="wide")

st.markdown("""
<style>

/* ---------------- APP ---------------- */

.stApp{
    background:#141414 !important;
}

[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
.main,
.block-container{
    background:#141414 !important;
}

section,main{
    background:#141414 !important;
}

/* ---------------- TEXT ---------------- */

*{
    color:white !important;
}

/* ---------------- SELECT BOX ---------------- */

[data-testid="stSelectbox"] > div > div{
    background:#222 !important;
    border:1px solid #444 !important;
    border-radius:10px !important;
    color:white !important;
}

/* Dropdown */

div[data-baseweb="popover"]{
    background:#1b1b1b !important;
    border:1px solid #333 !important;
}

div[data-baseweb="popover"] ul{
    background:#1b1b1b !important;
}

div[data-baseweb="popover"] li{
    background:#1b1b1b !important;
    color:white !important;
}

div[data-baseweb="popover"] li:hover{
    background:#E50914 !important;
}

div[data-baseweb="popover"] li[aria-selected="true"]{
    background:#B20710 !important;
}

/* ---------------- BUTTON ---------------- */

.stButton>button{
    background:#E50914 !important;
    color:white !important;
    border:none !important;
    border-radius:8px !important;
    font-weight:bold !important;
}

.stButton>button:hover{
    background:#B20710 !important;
}

/* ---------------- POSTERS ---------------- */

[data-testid="stImage"] img{
    border-radius:12px;
    transition:.25s;
}

[data-testid="stImage"] img:hover{
    transform:scale(1.05);
    box-shadow:0 0 18px rgba(229,9,20,.5);
}

</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------

st.markdown("""
<div style="text-align:center; padding-bottom:20px;">
    <h1 style="font-size:60px; font-weight:900;">
        🎬 CineMatch
    </h1>
    <p style="color:#bbbbbb;">
        Find movies similar to what you love 🍿
    </p>
</div>
""", unsafe_allow_html=True)

selected_movie = st.selectbox(
    "🔍 Choose a movie",
    movies["title"].values
)

if st.button("Get Recommendations"):

    with st.spinner("Finding movies you'll love... 🍿"):

        names, posters = recommend(selected_movie)

    st.markdown("## ✨ Recommended For You")

    cols = st.columns(5)

    for i in range(5):
        with cols[i]:

            if posters[i]:
                st.image(posters[i], width="stretch")
            else:
                st.write("No Poster")

            st.markdown(
                f"<center><b>{names[i]}</b></center>",
                unsafe_allow_html=True
            )