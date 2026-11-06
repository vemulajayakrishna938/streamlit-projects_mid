import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import re

st.set_page_config(page_title="IMDb Movie Analytics Dashboard", page_icon="🎬", layout="wide")
st.title("🎬 IMDb Movie Analytics Dashboard")
st.caption("Top 250 Movies | Explore • Analyze • Discover")

# ---- Dataset upload / load ----
@st.cache_data
def load_csv(file):
    return pd.read_csv(file)

uploaded = st.sidebar.file_uploader("Upload IMDb CSV dataset", type=["csv"])
default_path = Path(__file__).parent / "imdb_top_250.csv"
try:
    if uploaded is not None:
        raw = load_csv(uploaded)
    elif default_path.exists():
        raw = load_csv(default_path)
    else:
        st.warning("Upload your IMDb Top 250 CSV using the sidebar, or save it as Streamlit/imdb_top_250.csv.")
        st.stop()
except Exception as e:
    st.error(f"Could not read the CSV file: {e}")
    st.stop()

# Standardize common dataset column names

def normalize_name(x):
    return re.sub(r"[^a-z0-9]", "", str(x).lower())

column_lookup = {normalize_name(c): c for c in raw.columns}
aliases = {
    "title": ["title", "movietitle", "originaltitle", "primarytitle", "name"],
    "genres": ["genres", "genre"],
    "countries": ["countriesoforigin", "countries", "countryoforigin", "country", "origin"],
    "averageRating": ["averagerating", "imdbRating", "rating", "imdb_rating"],
    "numVotes": ["numvotes", "votes", "numberofvotes", "num_votes"],
    "grossWorldwide": ["grossworldwide", "worldwidegross", "gross", "worldwide_gross"]
}
rename = {}
for standard, names in aliases.items():
    for name in names:
        if normalize_name(name) in column_lookup:
            rename[column_lookup[normalize_name(name)]] = standard
            break

df = raw.rename(columns=rename).copy()
required = ["title", "genres", "averageRating", "numVotes", "grossWorldwide"]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error("Required columns not found: " + ", ".join(missing))
    st.write("CSV columns detected:", list(raw.columns))
    st.info("Use the IMDb Top 250 dataset specified by your question paper. Country column is optional; if absent, country filtering will be disabled.")
    st.stop()
if "countries" not in df.columns:
    df["countries"] = ""

# Clean numeric fields
def to_number(value):
    if pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", "").replace("$", "")
    multiplier = 1
    if s.upper().endswith("B"):
        multiplier, s = 1_000_000_000, s[:-1]
    elif s.upper().endswith("M"):
        multiplier, s = 1_000_000, s[:-1]
    elif s.upper().endswith("K"):
        multiplier, s = 1_000, s[:-1]
    try:
        return float(s) * multiplier
    except ValueError:
        return 0.0

df["averageRating"] = pd.to_numeric(df["averageRating"], errors="coerce")
df["numVotes"] = pd.to_numeric(df["numVotes"].apply(to_number), errors="coerce").fillna(0)
df["grossWorldwide"] = df["grossWorldwide"].apply(to_number)
df["title"] = df["title"].fillna("").astype(str)
df["genres"] = df["genres"].fillna("").astype(str)
df["countries"] = df["countries"].fillna("").astype(str)
df = df.dropna(subset=["averageRating"])

st.sidebar.success(f"Loaded {len(df):,} movies")
st.success("Dataset loaded successfully!")

# ---- Q1 Dataset loading and initial exploration ----
st.header("1. Dataset Loading and Preparation")
st.subheader("First 10 Records")
st.dataframe(df.head(10), use_container_width=True)
a, b = st.columns(2)
a.metric("Total Rows", df.shape[0])
b.metric("Total Columns", df.shape[1])
with st.expander("Dataset Information"):
    st.write("**Column names:**", list(df.columns))
    st.write("**Data types:**")
    st.dataframe(df.dtypes.astype(str).rename("Data Type"))
    st.write("**Missing values in each column:**")
    st.dataframe(df.isnull().sum().rename("Missing Values"))
st.divider()

# ---- Q2 KPI cards ----
st.header("2. Movie Analytics Dashboard")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Movies", f"{len(df):,}")
k2.metric("Average IMDb Rating", f"{df['averageRating'].mean():.2f}")
k3.metric("Highest Rating", f"{df['averageRating'].max():.1f}")
k4.metric("Total Votes", f"{df['numVotes'].sum():,.0f}")
st.divider()

# ---- Q3 and Q4 visualizations / tabs ----
st.header("3. Data Visualization")
genre_tab, rating_tab, gross_tab = st.tabs(["Genre Analysis", "Rating Analysis", "Gross Collection"])
with genre_tab:
    st.subheader("Movies by Genre")
    genre_series = df["genres"].str.split(r",\s*|\s*\|\s*").explode().str.strip()
    genre_counts = genre_series[genre_series.ne("")].value_counts()
    if not genre_counts.empty:
        st.bar_chart(genre_counts, x_label="Genre", y_label="Number of Movies")
    else:
        st.info("No genre values found in the dataset.")
with rating_tab:
    st.subheader("IMDb Rating Distribution")
    fig, ax = plt.subplots()
    ax.hist(df["averageRating"].dropna(), bins=15)
    ax.set_xlabel("IMDb Rating")
    ax.set_ylabel("Number of Movies")
    ax.set_title("Distribution of IMDb Ratings")
    st.pyplot(fig)
    plt.close(fig)
    st.subheader("Rating vs Number of Votes")
    fig, ax = plt.subplots()
    ax.scatter(df["averageRating"], df["numVotes"], alpha=0.7)
    ax.set_xlabel("IMDb Rating")
    ax.set_ylabel("Number of Votes")
    ax.set_title("IMDb Rating vs Number of Votes")
    st.pyplot(fig)
    plt.close(fig)
with gross_tab:
    st.subheader("Top 10 Movies by Worldwide Gross")
    top10 = df.nlargest(10, "grossWorldwide")
    if top10["grossWorldwide"].max() > 0:
        st.bar_chart(top10.set_index("title")["grossWorldwide"], x_label="Movie", y_label="Worldwide Gross (USD)")
        st.dataframe(top10[["title", "grossWorldwide"]], use_container_width=True)
    else:
        st.info("Worldwide gross data is unavailable or empty in this CSV.")
st.info("Use the tabs to explore genre, rating and worldwide gross analysis.")
st.divider()

# ---- Q5 Interactive Movie Explorer ----
st.header("4. Interactive Movie Explorer")
if "reset_explorer" not in st.session_state:
    st.session_state.reset_explorer = 0
if st.button("Reset Filters"):
    st.session_state.reset_explorer += 1
    st.rerun()
rkey = st.session_state.reset_explorer

def split_values(series):
    vals = set()
    for cell in series.fillna("").astype(str):
        for value in re.split(r",|\||;", cell):
            value = value.strip()
            if value:
                vals.add(value)
    return sorted(vals)

genres = split_values(df["genres"])
countries = split_values(df["countries"])
c1, c2, c3 = st.columns(3)
selected_genre = c1.selectbox("Genre", ["All"] + genres, key=f"genre_{rkey}")
selected_countries = c2.multiselect("Countries", countries, key=f"countries_{rkey}") if countries else []
min_rating, max_rating = c3.slider("IMDb Rating Range", 0.0, 10.0, (7.0, 10.0), 0.1, key=f"rating_{rkey}")
c4, c5, c6 = st.columns(3)
min_votes = c4.number_input("Minimum Votes", min_value=0, value=0, step=1000, key=f"votes_{rkey}")
search_title = c5.text_input("Search Title", key=f"title_{rkey}")
sort_order = c6.radio("Sort Order", ["Ascending", "Descending"], index=1, key=f"sort_{rkey}")
filtered = df.copy()
if selected_genre != "All":
    filtered = filtered[filtered["genres"].str.contains(re.escape(selected_genre), case=False, na=False)]
if selected_countries:
    pattern = "|".join(re.escape(x) for x in selected_countries)
    filtered = filtered[filtered["countries"].str.contains(pattern, case=False, na=False)]
filtered = filtered[filtered["averageRating"].between(min_rating, max_rating)]
filtered = filtered[filtered["numVotes"] >= min_votes]
if search_title.strip():
    filtered = filtered[filtered["title"].str.contains(search_title.strip(), case=False, na=False)]
filtered = filtered.sort_values("averageRating", ascending=(sort_order == "Ascending"))
st.metric("Filtered Movies", len(filtered))
st.dataframe(filtered, use_container_width=True)
st.divider()

# ---- Q6 Session state and form handling ----
st.header("5. Session State and Movie Search Form")
if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None
with st.form("movie_search_form"):
    form_title = st.text_input("Movie Title")
    form_genre = st.selectbox("Preferred Genre", ["All"] + genres)
    form_rating = st.slider("Minimum IMDb Rating", 0.0, 10.0, 7.0, 0.1)
    submitted = st.form_submit_button("Search Movie")
if submitted:
    result = df[df["title"].str.contains(form_title.strip(), case=False, na=False)] if form_title.strip() else df.copy()
    result = result[result["averageRating"] >= form_rating]
    if form_genre != "All":
        result = result[result["genres"].str.contains(re.escape(form_genre), case=False, na=False)]
    if not result.empty:
        st.session_state.selected_movie = result.sort_values("averageRating", ascending=False).iloc[0].to_dict()
    else:
        st.session_state.selected_movie = None
if st.session_state.selected_movie is not None:
    movie = st.session_state.selected_movie
    st.success("Movie found successfully!")
    m1, m2, m3 = st.columns(3)
    m1.metric("IMDb Rating", f"{movie['averageRating']:.1f}")
    m2.metric("Number of Votes", f"{movie['numVotes']:,.0f}")
    m3.write("**Genre**\n\n" + str(movie["genres"]))
    st.write("**Movie Title:**", movie["title"])
else:
    st.info("Enter search preferences and click Search Movie. Matching movie details will appear here.")

st.success("IMDb Movie Analytics Dashboard is ready!")
