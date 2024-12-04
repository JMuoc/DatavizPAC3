# %% Import libraries
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


# %% Graph definition functions
# Pie plots
def create_pie1(data):
    pie1 = (
        alt.Chart(data.reset_index())
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
    return pie1


def create_pie2(data):
    pie2 = (
        alt.Chart(data)
        .mark_arc(innerRadius=90)
        .encode(
            theta=alt.Theta(field="proportion", type="quantitative", title=""),
            color=alt.Color(
                field="continent",
                type="nominal",
                title="",
                scale=alt.Scale(
                    range=[
                        "#BBDEFB",
                        "#90CAF9",
                        "#64B5F6",
                        "#42A5F5",
                        "#1E88E5",
                        "#1565C0",
                        "#0D47A1",
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
    return pie2


# Line plots
def create_line_plot(
    hotel_data,
    value_column,
    filter_column=None,
    filter_value=None,
    color_value="#1565C0",
):
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

    # Apply filtering
    if filter_column and filter_value:
        Interat_perc_by_month_year = Interat_perc_by_month_year[
            Interat_perc_by_month_year[filter_column] == filter_value
        ]

    mean_adr_by_month_year["arrival_date"] = mean_adr_by_month_year[
        "arrival_date"
    ].astype(str)
    Interat_perc_by_month_year["arrival_date"] = Interat_perc_by_month_year[
        "arrival_date"
    ].astype(str)

    # Select data
    if value_column == "adr":
        data = mean_adr_by_month_year
        y_title = "Average Daily Rate (ADR)"
        y_field = "adr"
    elif value_column == "proportion":
        data = Interat_perc_by_month_year
        y_title = "International Bookings (%)"
        y_field = "proportion"
    else:
        raise ValueError("Invalid value_column. Choose 'adr' or 'proportion'.")

    # Create the line plot
    line_plot = (
        alt.Chart(data)
        .mark_line(point=True)
        .encode(
            x=alt.X("arrival_date:N", title="Month-Year", sort=None),
            y=alt.Y(f"{y_field}:Q", title=y_title),
            tooltip=[
                alt.Tooltip("arrival_date:N", title="Month-Year"),
                alt.Tooltip(f"{y_field}:Q", format=".2f", title=y_title),
            ],
            color=alt.value(color_value),
        )
        .interactive()
    )

    return line_plot


# Maps and bar charts
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
        .mark_bar()
        + alt.Chart(mean_adr_by_country)
        .encode(
            x=alt.X("country_y:N", title="", sort=None),
            y=alt.Y("adr:Q", title="Average Daily Rate (ADR)"),
            text=alt.Text("adr:Q", format=".2f"),
        )
        .mark_text(
            align="center",
            baseline="middle",
            color="black",
            size=17,
            dy=14,
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
    # Create dots map
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


# %% Page layout
# Set page config
st.set_page_config(layout="wide")
# Set page title and subheader for section 1
st.title("Tracking Back Tourist Revenue")
st.subheader("2017: Where are we now ?")

# Adding KPIs
st.markdown("<br>", unsafe_allow_html=True)
origin_countries = hotel_data["country_y"].nunique()
origin_continents = continent_perc_2017["continent"].nunique()
mean_adr_2017 = float(hotel_data["adr"][hotel_data["arrival_date_year"] == 2017].mean())
perc_international_2017 = float(Nat_Inter_perc_2017.loc["International"])

# Organize KPIs in columns
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
col1, col2 = st.columns(2)
# Organize charts in columns
with col1:
    with st.container(border=True):
        st.markdown(
            "<h3 style='font-size:24px;'>Total Bookings (%)</h3>",
            unsafe_allow_html=True,
        )
        st.altair_chart(
            create_pie1(Nat_Inter_perc_2017),
            theme="streamlit",
            use_container_width=True,
        )
        # Adding text
        st.markdown(
            """
            <span style="font-size:20px;">In 2017, <strong>69%</strong> of our bookings were <span style="color:#64B5F6;">**International**</span></span>.<br>
            """,
            unsafe_allow_html=True,
        )
with col2:
    with st.container(border=True):
        st.markdown(
            "<h3 style='font-size:24px;'>International Bookings (%)</h3>",
            unsafe_allow_html=True,
        )
        st.altair_chart(
            create_pie2(continent_perc_2017),
            theme="streamlit",
            use_container_width=True,
        )
        # Adding text
        st.markdown(
            """
            <span style="font-size:20px;">We had the most presence in <span style="color:#64B5F6;">**Europe** </span>**(87%)**, followed by <span style="color:#90CAF9;">**Asia** </span>**(6%)**.</span>
            """,
            unsafe_allow_html=True,
        )

# Line break
st.markdown("<br>", unsafe_allow_html=True)

# Subheader for section 2
st.subheader("History: How did we get here?")

# Adding line plots
col1, col2 = st.columns(2)
# organize charts in columns
with col1:
    st.markdown(
        "<h3 style='font-size:24px;'>Average Daily Rate Evolution</h3>",
        unsafe_allow_html=True,
    )
    st.altair_chart(
        create_line_plot(hotel_data, value_column="adr", color_value="#1565C0"),
        theme="streamlit",
        use_container_width=True,
    )
    # Adding text
    st.markdown(
        """
        <span style="font-size:20px;">Our <span style="color:#1565C0;">**ADR**</span> has raised consistently every summer.</span>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        "<h3 style='font-size:24px;'>International Bookings (%) Evolution</h3>",
        unsafe_allow_html=True,
    )
    st.altair_chart(
        create_line_plot(
            hotel_data,
            value_column="proportion",
            filter_column="National_tourist",
            filter_value="International",
            color_value="#FF9800",
        ),
        theme="streamlit",
        use_container_width=True,
    )
    st.markdown(
        """
        <span style="font-size:20px;">&nbsp;Our percentage of <span style="color:#FF9800;">**International Bookings** </span>has been in constant growth.</span>
        """,
        unsafe_allow_html=True,
    )

# Line break
st.markdown("<br>", unsafe_allow_html=True)

# Adding interactive evolution map
st.markdown(
    "<h3 style='font-size:24px;'>Countries of Origin Evolution</h3>",
    unsafe_allow_html=True,
)


# Function to filter data
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


# Adding Slider
# Get the first and last days
first_day = hotel_data["arrival_date"].min().date()
last_day = hotel_data["arrival_date"].max().date()
# Slider
selected_date = st.slider(
    "",
    min_value=first_day,
    max_value=last_day,
    value=first_day,
    format="YYYY-MM-DD",
)

# Filter data for the selected date
selected_day = pd.to_datetime(selected_date)
filtered_data_slider = get_filtered_data(selected_day)

# Map
st.map(filtered_data_slider)

# Adding text
st.markdown(
    """
    <span style="font-size:20px;">Over three years we have expaded to more than <span style="color:#FF4F55;">**6 continents**</span> and <span style="color:#FF4F55;">**173 countries**</span>.</span>
    """,
    unsafe_allow_html=True,
)

# Line break
st.markdown("<br>", unsafe_allow_html=True)

# Header for section 3
st.subheader("Expansion: What did we gain?")
# Map and bar plots
st.markdown(
    "<h3 style='font-size:24px;'>Top 10 Countries by ADR</h3>",
    unsafe_allow_html=True,
)
b1, m1 = create_charts(2015)
b2, m2 = create_charts(2016)
b3, m3 = create_charts(2017)
# Organize plots in tabs and columns
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
st.markdown(
    """
    <span style="font-size:20px;">Thanks to our expansion we have gained access to the <span style="color:#FF4F55;">**Eastern European**</span> and <span style="color:#FF4F55;">**Asian**</span> markets, thus attracting clients with consistently higher **ADRs**.</span>
    """,
    unsafe_allow_html=True,
)
