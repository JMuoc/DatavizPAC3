# %% Import libraries
import time

import altair as alt
import geopandas as gpd
import numpy as np
import pandas as pd
import streamlit as st

# %% Import Data
# Import hotels data
hotel_data = pd.read_csv("Resources/Cleaned Data/Clean_Hotel_Data.csv")
# Import country geodata
gdf = gpd.read_file("Resources/Country Data/ne_10m_admin_0_countries.shp")
# Import country continents
country_continents = pd.read_csv(
    "Resources/Country Data/countries_with_continents.csv",
    sep=",",
)

# %% Data Wrangling
# Add date column
hotel_data["arrival_date"] = (
    hotel_data["arrival_date_year"].astype(str)
    + "-"
    + hotel_data["arrival_date_month"].astype(str).str.zfill(2)
    + "-"
    + hotel_data["arrival_date_day_of_month"].astype(str).str.zfill(2)
)
hotel_data["arrival_date"] = pd.to_datetime(hotel_data["arrival_date"])
# Add national_tourist column
hotel_data["National_tourist"] = np.where(
    hotel_data["country"] == "PRT",
    "National",
    "International",
)
# Rename Chine country code to align with geo data
hotel_data["country"] = np.where(
    hotel_data["country"] == "CN",
    "CHN",
    hotel_data["country"],
)
# Drop nan countries
hotel_data = hotel_data.dropna(subset=["country"])
# Extract the centroid coordinates from country data
gdf["centroid"] = gdf.geometry.centroid
gdf["latitude"] = gdf["centroid"].y
gdf["longitude"] = gdf["centroid"].x
# Add country coordinates
hotel_data = hotel_data.merge(
    gdf[["ADMIN", "latitude", "longitude", "ADM0_A3"]],
    left_on="country",
    right_on="ADM0_A3",
    how="left",
)
# Rename columns
hotel_data = hotel_data.rename(columns={"ADMIN": "country_name"})
# Add country continents
hotel_data = hotel_data.merge(
    country_continents,
    left_on="country_name",
    right_on="country",
    how="left",
)
# National/International tourism percentages
Nat_Inter_perc_2017 = (
    hotel_data["National_tourist"][
        hotel_data["arrival_date_year"] == 2017
    ].value_counts(normalize=True)
    * 100
)
# Continents percentages
continent_perc_2017 = (
    hotel_data["continent"][hotel_data["arrival_date_year"] == 2017].value_counts(
        normalize=True,
    )
    * 100
).reset_index()
# Rename columns
continent_perc_2017 = continent_perc_2017[continent_perc_2017["proportion"] > 0.008]

# %% Page layout
st.set_page_config(layout="wide")
st.title("Tracking Back Tourist Revenue")
st.subheader("2017: Where are we now ?")

# Adding KPIs
st.markdown("<br>", unsafe_allow_html=True)
origin_countries = hotel_data["country_y"].nunique()
origin_continents = continent_perc_2017["continent"].nunique()
mean_adr_2017 = float(hotel_data["adr"][hotel_data["arrival_date_year"] == 2017].mean())
perc_international_2017 = float(Nat_Inter_perc_2017.loc["International"])

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("**COUNTRIES OF ORIGIN**", f"{origin_countries}")

with col2:
    st.metric("**CONTINENTS**", f"{origin_continents}")

with col3:
    st.metric("**INTERNATIONAL BOOKINGS**", f"{perc_international_2017:.1f} %")

with col4:
    st.metric("**AVERAGE DAILY RATE**", f"{mean_adr_2017:.1f}")
# Adding Pie Charts
pie1 = (
    alt.Chart(Nat_Inter_perc_2017.reset_index())
    .mark_arc(innerRadius=50)
    .encode(
        theta=alt.Theta(field="proportion", type="quantitative", title=""),
        color=alt.Color(
            field="National_tourist",
            type="nominal",
            title="",
            scale=alt.Scale(range=["#64B5F6", "#E57373"]),
        ),
        tooltip=[
            alt.Tooltip("National_tourist:N", title=""),
            alt.Tooltip("proportion:Q", format=".2f", title="Percentage"),
        ],
    )
    .interactive()
)
pie2 = (
    alt.Chart(continent_perc_2017)
    .mark_arc(innerRadius=90)
    .encode(
        theta=alt.Theta(field="proportion", type="quantitative", title=""),
        color=alt.Color(
            field="continent",
            type="nominal",
            title="",
            scale=alt.Scale(
                range=[
                    "#BBDEFB",  # Pale blue
                    "#90CAF9",  # Lighter blue
                    "#64B5F6",  # Softer medium blue
                    "#42A5F5",  # Rich medium blue
                    "#1E88E5",  # Vivid blue
                    "#1565C0",  # Deep blue
                    "#0D47A1",  # Darker, richer blue
                ],
            ),
        ),
        tooltip=[
            alt.Tooltip("continent:N", title=""),
            alt.Tooltip("proportion:Q", format=".2f", title="Percentage"),
        ],
    )
    .interactive()
)
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown(
            "<h3 style='font-size:24px;'>Total Bookings (%)</h3>",
            unsafe_allow_html=True,
        )
        st.altair_chart(pie1, theme="streamlit", use_container_width=True)

with col2:
    with st.container(border=True):
        st.markdown(
            "<h3 style='font-size:24px;'>International Bookings (%)</h3>",
            unsafe_allow_html=True,
        )
        st.altair_chart(pie2, theme="streamlit", use_container_width=True)

# Line break
st.markdown("<br>", unsafe_allow_html=True)
# Header
st.subheader("History: How did we get here?")
# Line plots dfs
mean_adr_by_month_year = (
    hotel_data.groupby(hotel_data["arrival_date"].dt.to_period("M"))["adr"]
    .mean()
    .reset_index()
)
Interat_perc_by_month_year = (
    hotel_data.groupby(hotel_data["arrival_date"].dt.to_period("M"))[
        "National_tourist"
    ].value_counts(normalize=True)
    * 100
).reset_index()
Interat_perc_by_month_year = Interat_perc_by_month_year[
    Interat_perc_by_month_year["National_tourist"] == "International"
]
# Add month labels
mean_adr_by_month_year["arrival_date"] = mean_adr_by_month_year["arrival_date"].astype(
    str,
)
Interat_perc_by_month_year["arrival_date"] = Interat_perc_by_month_year[
    "arrival_date"
].astype(str)
# Plots
line_plot1 = (
    alt.Chart(mean_adr_by_month_year)
    .mark_line(point=True)
    .encode(
        x=alt.X("arrival_date:N", title="Month-Year", sort=None),
        y=alt.Y("adr:Q", title="Average Daily Rate (ADR)"),
        tooltip=[
            alt.Tooltip("arrival_date:N", title="Month-Year"),
            alt.Tooltip("adr:Q", format=".2f", title="Mean ADR"),
        ],
        color=alt.value("#1565C0"),
    )
    .interactive()
)
line_plot2 = (
    alt.Chart(Interat_perc_by_month_year)
    .mark_line(point=True)
    .encode(
        x=alt.X("arrival_date:N", title="Month-Year", sort=None),
        y=alt.Y("proportion:Q", title="International Bookings(%)"),
        tooltip=[
            alt.Tooltip("arrival_date:N", title="Month-Year"),
            alt.Tooltip("proportion:Q", format=".2f", title="Percentage"),
        ],
        color=alt.value("#FF9800"),
    )
    .interactive()
)
col1, col2 = st.columns(2)

with col1:
    st.markdown(
        "<h3 style='font-size:24px;'>Average Daily Rate Evolution</h3>",
        unsafe_allow_html=True,
    )
    st.altair_chart(line_plot1, theme="streamlit", use_container_width=True)

with col2:
    st.markdown(
        "<h3 style='font-size:24px;'>International Bookings (%) Evolution</h3>",
        unsafe_allow_html=True,
    )
    st.altair_chart(line_plot2, theme="streamlit", use_container_width=True)

# Adding map
st.markdown(
    "<h3 style='font-size:24px;'>Countries of origin evolution</h3>",
    unsafe_allow_html=True,
)
# Play button
play_button = st.button("Play", type="primary")
# Line break
st.markdown("<br>", unsafe_allow_html=True)


# Prepare the df_for_map DataFrame
def get_filtered_data(day):
    df_for_map = hotel_data[hotel_data["arrival_date"] <= day]
    df_for_map = (
        df_for_map[
            df_for_map["country_y"].isin(
                df_for_map["country_y"]
                .value_counts()[df_for_map["country_y"].value_counts() > 5]
                .index,
            )
        ][["country_name", "latitude", "longitude"]]
    ).drop_duplicates()
    return df_for_map


# Get the first day (earliest date) data
first_day = sorted(hotel_data["arrival_date"].unique())[0]
df_for_map = get_filtered_data(first_day)
# Create an empty container for the map
map_placeholder = st.empty()
# Initially display the map with data from the first day
map_placeholder.map(df_for_map)
# Create a placeholder for the year text
year_placeholder = st.empty()
# Create a function for the animation when the play button is clicked


def evol_animation():
    # Loop through the dates to simulate the animation
    for day in sorted(hotel_data["arrival_date"].unique()):
        df_for_map = get_filtered_data(day)
        map_placeholder.map(df_for_map)
        current_year = pd.to_datetime(str(day)).year
        year_placeholder.write(f"Year: {current_year}")
        time.sleep(0.01)


# Run the animation when the play button is clicked
if play_button:
    evol_animation()
# Line break
st.markdown("<br>", unsafe_allow_html=True)


def create_charts(year):
    # Calculate mean ADR by country
    mean_adr_by_country = (
        hotel_data[hotel_data["arrival_date_year"] == year]
        .assign(
            country_count=lambda df: df.groupby("country_y")["country_y"].transform(
                "count",
            ),
        )
        .query("country_count > 5")
        .groupby("country_y", as_index=False)
        .mean("adr")
        .sort_values("adr", ascending=False)
        .head(5)
    )
    # Bar chart
    custom_palette = ["#6EC1E4", "#4CAF50", "#FF6F61", "#00BCD4", "#607D8B"]
    bar_chart = (
        alt.Chart(mean_adr_by_country)
        .mark_bar()
        .encode(
            y=alt.Y("adr:Q", title="Average Daily Rate (ADR)"),
            x=alt.X("country_y:N", title="", sort=None),
            color=alt.Color(
                "country_y:N",
                scale=alt.Scale(
                    domain=mean_adr_by_country["country_y"].unique().tolist(),
                    range=custom_palette,
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("country_y:N", title="Country"),
                alt.Tooltip("adr:Q", format=".2f", title="ADR"),
            ],
        )
        .interactive()
    )
    # Create the background map
    world = alt.topo_feature(
        "https://raw.githubusercontent.com/vega/vega-datasets/master/data/world-110m.json",
        feature="countries",
    )
    background = (
        alt.Chart(world)
        .mark_geoshape(fill="#333333", stroke="dimgrey")
        .project("naturalEarth1")
    )
    mean_adr_by_country["adr_squared"] = np.square(mean_adr_by_country["adr"])
    # Create dots
    map_chart = (
        alt.Chart(mean_adr_by_country)
        .mark_circle(opacity=0.8, stroke="black", strokeWidth=1)
        .encode(
            longitude="longitude:Q",
            latitude="latitude:Q",
            size=alt.Size(
                "adr_squared:Q",
                title="ADR",
                scale=alt.Scale(range=[50, 2500]),
            ),
            tooltip=[
                alt.Tooltip("country_y:N", title="Country"),
                alt.Tooltip("adr:Q", format=".2f", title="ADR"),
            ],
            color=alt.value("#FF6347"),
        )
    )
    final_map = background + map_chart
    return bar_chart, final_map

# Header
st.subheader("Expansion: What did we gain?")
# Plot
st.markdown(
        "<h3 style='font-size:24px;'>Top 10 Countries by ADR</h3>",
        unsafe_allow_html=True,
    )
b1, m1 = create_charts(2015)
b2, m2 = create_charts(2016)
b3, m3 = create_charts(2017)
tab1, tab2, tab3 = st.tabs(["2015", "2016", "2017"])
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        with st.container():
            st.altair_chart(b1, use_container_width=True)

    with col2:
        with st.container():
            st.altair_chart(m1.interactive(), use_container_width=True)
with tab2:
    col1, col2 = st.columns(2)
    with col1:
        with st.container():
            st.altair_chart(b2, use_container_width=True)

    with col2:
        with st.container():
            st.altair_chart(m2.interactive(), use_container_width=True)
with tab3:
    col1, col2 = st.columns(2)
    with col1:
        with st.container():
            st.altair_chart(b3, use_container_width=True)

    with col2:
        with st.container():
            st.altair_chart(m3.interactive(), use_container_width=True)


# Add some text and numbers in the bar charts and pie charts it would be nice