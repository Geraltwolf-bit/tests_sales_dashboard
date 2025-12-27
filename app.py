import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import json
from shapely import wkt

st.set_page_config(
    page_title='Sales per year',
    page_icon='',
    layout='wide',
    initial_sidebar_state='expanded'
)

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

gdf = pd.read_csv('gdf.csv')

def wkt_to_geojson(wkt_str) -> dict:
    """ 
    Convert wkt-text into a GeoJSON dictionary that Plotly can use to draw maps
    Arguments: wkt text
    Returns: a Python dictionary in GeoJSON format
    """
    geom = wkt.loads(wkt_str)
    return json.loads(json.dumps(geom.__geo_interface__))

gdf['geometry'] = gdf['geometry'].apply(wkt_to_geojson)

def format_number(num: int) -> str:
    """
    Transforms long numbers into a readable format.
    Arguments: int
    Returns: str
    """
    if num > 1_000_000:
        if num % 1_000_000 == 0:
            return f'{num // 1_000_000} M'
        return f'{round(num / 1_000_000, 1)} M'
    return f'{num // 1000} K'

@st.cache_data
def load_data(file_path):
    """
    Load data using cashing decorator that cashes the output.
    Function doesn't reload every time a user interacts with the dashboard.
    """
    return pd.read_csv(file_path)

disease_files = {
    'Гепатит С': 'df.csv',
    'Гепатит В': 'hep_b.csv',
    'ВИЧ': 'hiv.csv'
}

with st.sidebar:
    st.title('Закупки тестов Минздравом')
    disease_list = list(disease_files.keys())
    selected_disease = st.selectbox('Выберите заболевание', disease_list)
    
    df = load_data(disease_files[selected_disease])
    
    year_list = sorted(df['year'].unique(), reverse=True)
    selected_year = st.selectbox('Выберите год', year_list)
        
def choropleth(df, gdf, year) -> go.Figure:
    """
    Creates a choropleth map that shows the number of items for each region.
    Arguments: 
        df: sales data with columns ['year', 'region', 'quantity']
        gdf: Geographic data with columns ['name', 'geometry']
        year: year to display
    Returns: plotly.graph_objects.Figure: choropleth map
    """
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
        range_color=[0, 100_000]
    )

    fig.update_geos(
        projection_type = 'mercator',
        visible=False,
        showcountries = False,
        showcoastlines = False,
        showland = False,
        showocean = False,
        showframe = False,
        lonaxis_range = [20, 180],
        lataxis_range = [20, 80],
    )

    fig.update_layout(margin = {'r': 0, 't': 50, 'l': 0, 'b': 0},
        height = 600)

    return fig

col = st.columns(1)

with col[0]:
    
    fig = choropleth(df, gdf, selected_year)
    st.plotly_chart(fig, use_container_width=True)
    
    col_1, col_2, col_3, col_4, col_5 = st.columns(5)
    
    with col_1:
        total_sales = df[df['year'] == selected_year]['total'].sum()
        total_sales_formatted = format_number(total_sales)
        st.metric(label = 'Объём закупок, руб.', value = total_sales_formatted, border = True, height = 'content', width = 'stretch')
    
    with col_2:
        total_quantity = df[df['year'] == selected_year]['quantity'].sum()
        total_quantity_formatted = format_number(total_quantity)
        st.metric(label = 'Количество тестов, шт.', value = total_quantity_formatted, border = True, height = 'content', width = 'stretch')
    
    with col_3:
        max_price = df[df['year'] == selected_year]['price'].max()
        st.metric(label = 'Максимальная цена', value = f'{max_price:,.2f}', border = True, height = 'content', width = 'stretch')
    
    with col_4:
        mean_price = df[df['year'] == selected_year]['price'].mean()
        st.metric(label = 'Средняя цена', value = f'{mean_price:,.2f}', border = True, height = 'content', width = 'stretch')

    with col_5:
        min_price = df[df['year'] == selected_year]['price'].min()
        st.metric(label = 'Минимальная цена', value = f'{min_price:,.2f}', border = True, height = 'content', width = 'stretch')
    
    st.markdown(f'<h4 style="text-align: center;">Топ 5 регионов в {selected_year}:</h4>', unsafe_allow_html = True)
    
    col_top_5_price, col_top_5_amount = st.columns(2)
    
    with col_top_5_price:
        st.markdown('##### По объёму закупок в рублях')
        yearly_data = df[df['year'] == selected_year]
        region_sales = yearly_data.groupby('region')['total'].sum().reset_index()
        region_sales = region_sales.sort_values(by = 'total', ascending = False)
        top5 = region_sales.head(5)
    
        for i, (region, sales) in enumerate(zip(top5['region'], top5['total']), 1):
            st.write(f'{i}) {region}: {sales:,.2f}')
    
    with col_top_5_amount:
        st.markdown('##### По цене')    
        region_price = yearly_data.groupby('region')['price'].max().reset_index()
        region_price = region_price.sort_values(by = 'price', ascending = False)
        top_5 = region_price.head(5)
        
        for i, (region, price) in enumerate(zip(top_5['region'], top_5['price']), 1):
            st.write(f'{i}) {region}: {price:,.2f}')
    
    st.markdown(f'<h4 style="text-align: center;">Выводы за 2022 - 2024:</h4>', unsafe_allow_html = True)
    
    total = df.groupby('year')['total'].sum().reset_index()
    tot_trend = 'падает' if total.iloc[0, 1] > total.iloc[2, 1] else 'растет'
    fig = px.line(total, x = 'year', y = 'total', text = 'total', title = f'Объём закупок по выбранному заболеванию в рублях - {tot_trend}')
    fig.update_xaxes(tickmode = 'linear', dtick = 1, tickformat = 'd')
    fig.update_yaxes(tickformat = ',.0f')
    fig.update_traces(texttemplate="%{y:.3s}", textposition = 'top center')
    st.plotly_chart(fig, use_container_width=True)

    price = df.groupby('year')['price'].mean().reset_index()
    price_trend = 'растет' if total.iloc[0, 1] > total.iloc[2, 1] else 'падает'
    fig = px.line(price, x = 'year', y = 'price', text = 'price', title = f'Цена - {price_trend}')
    fig.update_traces(texttemplate = '%{text:,.0f}', textposition = 'top center')
    fig.update_xaxes(tickmode = 'linear', dtick = 1, tickformat = 'd')
    fig.update_yaxes(tickformat = ',.0f')
    st.plotly_chart(fig, use_container_width=True)



