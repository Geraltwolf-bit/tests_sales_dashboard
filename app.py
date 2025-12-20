import pandas as pd
import streamlit as st
import plotly.express as px
import altair as alt
import json
from shapely import wkt
from shapely.geometry import shape

st.set_page_config(
    page_title='Sales per year',
    page_icon='',
    layout='wide',
    initial_sidebar_state='expanded'
)

alt.themes.enable('dark')

st.markdown("""
<style>
[data-testid = 'block-container']{
            padding-left: 2rem;
            padding-right: 2rem;
            padding-top: 1rem;
            padding-bottom: 0rem;
            margin-bottom: -7remm;
            }

[data-testid='stVerticalBlock']{
            padding-left: 0rem;
            padding-right: 0rem;
            }

[data-testid='stMetric']{
            background-colr: #393939;
            text-align: center;
            padding: 15px 0;
            }

[data-testid='stMetricLabel']{
            display: flex;
            justify-content: center;
            align-items: center;
            }

[data-testid = 'stMetricDeltaIcon-Up']{
            position: relative;
            left: 38%;
            -webkit-transform: translateX(-50%);
            -ms-transform: translateX(-50%);
            transform: translateX(-50%);
            }

[data-testid='stMetricDeltaIcon-Down']{
            position: relative;
            left: 38%;
            -webkit-transform: translateX(-50%);
            -ms-transform: translateX(-50%);
            transform: translateX(-50%);
            }

</style>
""", unsafe_allow_html=True
)

df = pd.read_csv('df.csv')
gdf = pd.read_csv('gdf.csv')

def wkt_to_geojson(wkt_str):
    geom = wkt.loads(wkt_str)
    return json.loads(json.dumps(geom.__geo_interface__))

gdf['geometry'] = gdf['geometry'].apply(wkt_to_geojson)

with st.sidebar:
    st.title('Yearly sales')
    year_list = list(df.year.unique())[::-1]
    selected_year = st.selectbox('Select a year', year_list)

def choropleth(df, gdf, year):

    sales_year = df[df['year']==year].copy()
    agg_sales = sales_year.groupby('region').agg({'quantity': 'sum'}).reset_index()

    merged_data = gdf.merge(agg_sales, left_on='name', right_on='region', how='left')
    merged_data['quantity'] = merged_data['quantity'].fillna(0)

    geojson_dict = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "id": str(i), "geometry": row['geometry']}
            for i, row in merged_data.iterrows()
        ]
    }

    fig = px.choropleth(
        merged_data,
        geojson = geojson_dict,
        locations = merged_data.index.astype(str),
        color = 'quantity',
        color_continuous_scale='Blues',
        hover_name='name',
        hover_data={'quantity': ':,.0f'},
        title = f'Regional sales - {year}'
    )

    fig.update_geos(
        fitbounds = 'locations',
        visible=False,
        showcountries = False,
        showcoastlines = False
    )

    fig.update_layout(
        margin = {'r': 0, 't': 50, 'l': 0, 'b': 0},
        height = 600
    )

    return fig

col = st.columns((1.5, 4.5, 2), gap = 'medium')

with col[0]:
    st.markdown('### Max price')

with col[1]:
    fig = choropleth(df, gdf, selected_year)
    st.plotly_chart(fig, use_container_width=True)

with col[2]:
    st.markdown('### Min price')