import ee
import folium
import time
from google.colab import drive

# Authenticate and initialize Earth Engine


# Get user input for city
city_name = input("Enter city name: ")

# Define the AOI as the boundary of the selected city
admin_boundaries = ee.FeatureCollection('FAO/GAUL/2015/level2')
city_boundary = admin_boundaries.filter(ee.Filter.eq('ADM2_NAME', city_name))
aoi = city_boundary.geometry()

if city_boundary.size().getInfo() == 0:
    raise ValueError(f"City '{city_name}' not found in the database. Please check spelling and try again.")

# Function to apply scale factors to Landsat 8 image
def apply_scale_factors(image):
    optical_bands = image.select('SR_B.*').multiply(0.0000275).add(-0.2)
    return image.addBands(optical_bands, None, True)

# Function to mask clouds
def mask_l8sr(image):
    cloud_shadow_bit_mask = (1 << 3)
    clouds_bit_mask = (1 << 5)
    qa = image.select('QA_PIXEL')
    mask = qa.bitwiseAnd(cloud_shadow_bit_mask).eq(0).And(qa.bitwiseAnd(clouds_bit_mask).eq(0))
    return image.updateMask(mask)

# Function to calculate NDVI and classify vegetation density
def calculate_ndvi(image):
    ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
    vegetation_classes = ndvi.expression(
        "(b('NDVI') < 0.2) ? 1 : (b('NDVI') < 0.5) ? 2 : 3"
    ).rename('VegetationDensity')
    return vegetation_classes

# Function to calculate albedo
def calculate_albedo(image):
    coefficients = {'SR_B2': 0.356, 'SR_B3': 0.130, 'SR_B4': 0.373, 'SR_B5': 0.085, 'SR_B6': 0.072, 'SR_B7': -0.0018}
    albedo = ee.Image(0)
    for band, coeff in coefficients.items():
        albedo = albedo.add(image.select(band).multiply(coeff))
    albedo = albedo.add(0.016).max(0).min(1).multiply(100).rename('albedo')
    return albedo

# Get image collection for a specific year with cloud cover filtering
def get_image_collection(year):
    start_date, end_date = f'{year}-01-01', f'{year}-12-31'
    collection = (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
                  .filterDate(start_date, end_date)
                  .filterBounds(aoi)
                  .filter(ee.Filter.lt('CLOUD_COVER', 20))  # Filter by cloud cover
                  .map(apply_scale_factors)
                  .map(mask_l8sr))
    if collection.size().getInfo() == 0:
        raise ValueError(f"No Landsat 8 images found for {city_name} in {year}")
    return collection

# Visualization parameters
vegetation_vis = {'min': 1, 'max': 3, 'palette': ['#d73027', '#fee08b', '#1a9850']}
albedo_vis = {'min': 0, 'max': 60, 'palette': ['#2C1A5A', '#4B2991', '#6B3894', '#8B4984', '#AB5C6C', '#CB7152', '#EB8A36', '#FBA21B', '#F8C91E', '#F2E627', '#FFFFFF']}

# Create map
city_center = aoi.centroid().coordinates().getInfo()
Map = folium.Map(location=[city_center[1], city_center[0]], zoom_start=11)

# Function to add EE layers to folium map
def add_ee_layer(image, vis_params, name):
    map_id_dict = ee.Image(image).getMapId(vis_params)
    folium.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        name=name,
        overlay=True,
        control=True
    ).add_to(Map)

# Extract statistics function
def extract_statistics(image, aoi):
    mean_value = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=30,
        maxPixels=1e10
    ).getInfo()
    return mean_value

# Temporal analysis for multiple years
def temporal_analysis(start_year, end_year):
    temporal_vegetation = []
    temporal_albedo = []

    for year in range(start_year, end_year + 1):
        print(f"Processing year: {year}")
        start_time = time.time()

        collection = get_image_collection(str(year))
        median_image = collection.median()
        vegetation_image = calculate_ndvi(median_image).clip(aoi)
        albedo_image = calculate_albedo(median_image).clip(aoi)

        vegetation_mean = extract_statistics(vegetation_image, aoi)
        albedo_mean = extract_statistics(albedo_image, aoi)

        temporal_vegetation.append(vegetation_mean['VegetationDensity'])
        temporal_albedo.append(albedo_mean['albedo'])

        print(f"Year {year} completed in {time.time() - start_time:.2f} seconds.")

    return temporal_vegetation, temporal_albedo

# Run temporal analysis from 2015 to 2020
try:
    temporal_vegetation, temporal_albedo = temporal_analysis(2015, 2020)
    print(f"Temporal Vegetation Density (2015-2020): {temporal_vegetation}")
    print(f"Temporal Albedo (2015-2020): {temporal_albedo}")
except Exception as e:
    print(f"Error during temporal analysis: {e}")

# Process the latest year (2023)
try:
    year = '2023'
    print(f"Processing year: {year}")
    collection = get_image_collection(year)
    median_image = collection.median()

    # Calculate vegetation density clusters and albedo
    vegetation_image = calculate_ndvi(median_image).clip(aoi)
    albedo_image = calculate_albedo(median_image).clip(aoi)

    # Add layers to map for the latest year
    add_ee_layer(vegetation_image, vegetation_vis, 'Vegetation Density (2023)')
    add_ee_layer(albedo_image, albedo_vis, 'Albedo (2023)')
    folium.LayerControl().add_to(Map)

    print(f"Year {year} completed.")
except Exception as e:
    print(f"Error processing year {year}: {e}")

# Add legend to map
legend_html = """
<div style="
    position: fixed;
    top: 50%; left: 20px;
    transform: translateY(-50%);
    width: 220px;
    background-color: white;
    z-index: 9999;
    font-size: 14px;
    border: 2px solid grey;
    padding: 10px;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
">
    <b>Legend</b><br>
    <div style="display: flex; align-items: center;">
        <div style="width: 18px; height: 18px; background: #d73027; margin-right: 8px;"></div> Low Vegetation
    </div>
    <div style="display: flex; align-items: center;">
        <div style="width: 18px; height: 18px; background: #fee08b; margin-right: 8px;"></div> Medium Vegetation
    </div>
    <div style="display: flex; align-items: center;">
        <div style="width: 18px; height: 18px; background: #1a9850; margin-right: 8px;"></div> High Vegetation
    </div>
    <br>
    <b>Albedo Scale:</b><br>
    <div style="display: flex; align-items: center;">
        <div style="width: 18px; height: 18px; background: #2C1A5A; margin-right: 8px;"></div> Low Albedo
    </div>
    <div style="display: flex; align-items: center;">
        <div style="width: 18px; height: 18px; background: #F2E627; margin-right: 8px;"></div> High Albedo
    </div>
</div>
"""

Map.get_root().html.add_child(folium.Element(legend_html))

# Add a compass rose (direction scale) to the map
compass_rose_html = """
<div style="
    position: fixed;
    top: 50%; right: 50px;
    transform: translateY(-50%);
    width: 200px; height: 200px;
    z-index: 9999;">
    <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Brosen_windrose.svg/300px-Brosen_windrose.svg.png"
         style="width: 100%; height: 100%;"/>
</div>
"""

Map.get_root().html.add_child(folium.Element(compass_rose_html))

# Display map
Map
