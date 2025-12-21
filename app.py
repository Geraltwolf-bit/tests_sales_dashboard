import pandas as pd
import streamlit as st
import plotly.express as px
import altair as alt
import json
import matplotlib.pyplot as plt
import seaborn as sns
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

def format_number(num):
    if num > 1_000_000:
        if num % 1_000_000 == 0:
            return f'{num // 1_000_000} M'
        return f'{round(num / 1_000_000, 1)} M'
    return f'{num // 1000} K'

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
    st.markdown(f'### In {selected_year}:')
    
    total_sales = df[df['year'] == selected_year]['total'].sum()
    total_sales_formatted = format_number(total_sales)
    st.metric(label = 'Total sum', value = total_sales_formatted, border = True, height = 'content', width = 'stretch')
    
    total_quantity = df[df['year'] == selected_year]['quantity'].sum()
    total_quantity_formatted = format_number(total_quantity)
    st.metric(label = 'Total quantity', value = total_quantity_formatted, border = True, height = 'content', width = 'stretch')
    
    max_price = df[df['year'] == selected_year]['price'].max()
    st.metric(label = 'Max price', value = f'{max_price:,.2f}', border = True, height = 'content', width = 'stretch')
    
    min_price = df[df['year'] == selected_year]['price'].min()
    st.metric(label = 'Min price', value = f'{min_price:,.2f}', border = True, height = 'content', width = 'stretch')
    
    mean_price = df[df['year'] == selected_year]['price'].mean()
    st.metric(label = 'Mean price', value = f'{mean_price:,.2f}', border = True, height = 'content', width = 'stretch')
    
with col[1]:
    fig = choropleth(df, gdf, selected_year)
    st.plotly_chart(fig, use_container_width=True)
    
    total = df.groupby('year')['total'].sum().reset_index()
    fig = px.line(total, x = 'year', y = 'total', text = 'total', title = 'Total over the years, RUB')
    fig.update_traces(texttemplate = '%{text:,.0f}', textposition = 'top center')
    fig.update_xaxes(tickmode = 'linear', dtick = 1, tickformat = 'd')
    fig.update_yaxes(tickformat = ',.0f')
    st.plotly_chart(fig, use_container_width=True)
    
    price = df.groupby('year')['price'].mean().reset_index()
    fig = px.line(price, x = 'year', y = 'price', text = 'price', title = 'Mean price over the years, RUB')
    fig.update_traces(texttemplate = '%{text:,.0f}', textposition = 'top center')
    fig.update_xaxes(tickmode = 'linear', dtick = 1, tickformat = 'd')
    fig.update_yaxes(tickformat = ',.0f')
    st.plotly_chart(fig, use_container_width=True)


with col[2]:
    st.markdown(f'#### Top 5 regions in {selected_year}:')
    
    st.markdown('##### By amount')
    yearly_data = df[df['year'] == selected_year]
    region_sales = yearly_data.groupby('region')['total'].sum().reset_index()
    region_sales = region_sales.sort_values(by = 'total', ascending = False)
    top5 = region_sales.head(5)
    
    for i, (region, sales) in enumerate(zip(top5['region'], top5['total']), 1):
        st.write(f'{i}) {region}: {sales:,.2f}')
    
    st.markdown('##### By price')    
    region_price = yearly_data.groupby('region')['price'].max().reset_index()
    region_price = region_price.sort_values(by = 'price', ascending = False)
    top_5 = region_price.head(5)
    
    for i, (region, price) in enumerate(zip(top_5['region'], top_5['price']), 1):
        st.write(f'{i}) {region}: {price:,.2f}')