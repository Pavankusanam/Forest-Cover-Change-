import streamlit as st
import ee
import geemap.foliumap as geemap
import pandas as pd
import altair as alt

# Initialize the Earth Engine API
try:
    ee.Initialize(project='ee-pavankusanam81')
except Exception as e:
    ee.Authenticate()
    ee.Initialize()

def main():
    st.title("Forest Cover Change Detection")

    st.markdown("""
    This Streamlit app displays forest cover change using the JAXA/ALOS/PALSAR datasets.
    """)

    # User inputs for defining the region of interest
    st.subheader("Select Region of Interest")
    min_lat = st.number_input("Min Latitude", value=10.0, format="%.6f")
    max_lat = st.number_input("Max Latitude", value=11.0, format="%.6f")
    min_lon = st.number_input("Min Longitude", value=75.0, format="%.6f")
    max_lon = st.number_input("Max Longitude", value=76.0, format="%.6f")

    # Define the region of interest
    roi = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])

    # Load the image collections
    fnf_old = ee.ImageCollection("JAXA/ALOS/PALSAR/YEARLY/FNF")
    fnf_new = ee.ImageCollection("JAXA/ALOS/PALSAR/YEARLY/FNF4")
    fnf_combined = fnf_old.merge(fnf_new).sort("system:time_start")

    # Function to calculate forest area in the ROI
    def calculate_forest_area(image):
        forest_mask = image.select('fnf').eq(1)
        area_image = ee.Image.pixelArea().divide(10000).updateMask(forest_mask)
        forest_area = area_image.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=roi,
            scale=25,
            maxPixels=1e9
        ).get('area')
        return ee.Feature(None, {
            'year': ee.Date(image.get('system:time_start')).get('year'),
            'forest_area': forest_area
        })

    # Calculate forest area for each year
    forest_area_fc = fnf_combined.map(calculate_forest_area)
    forest_area_list = forest_area_fc.getInfo()['features']

    # Convert list to DataFrame
    data = [{
        'year': f['properties']['year'],
        'forest_area': f['properties']['forest_area']
    } for f in forest_area_list if f['properties']['forest_area'] is not None]

    df = pd.DataFrame(data).sort_values('year')

    # Plotting the time series
    st.subheader("Forest Cover over Time")
    if not df.empty:
        chart = alt.Chart(df).mark_line(point=True).encode(
            x='year:O',
            y='forest_area:Q',
            tooltip=['year', 'forest_area']
        ).interactive()
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No forest data available for this region.")

    # Display the map
    st.subheader("Map of Selected Region")
    m = geemap.Map(center=[(min_lat + max_lat) / 2, (min_lon + max_lon) / 2], zoom=6)
    m.addLayer(fnf_combined.sort('system:time_start', False).first().select('fnf'), 
               {'min': 1, 'max': 3, 'palette': ['006400', 'ffff00', '0000FF']}, 
               'Forest/Non-Forest')
    m.addLayer(roi, {}, 'ROI', opacity=0.4)
    m.to_streamlit(width=700, height=500)

if __name__ == "__main__":
    main()