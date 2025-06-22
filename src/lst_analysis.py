import ee
import folium
import google.generativeai as genai



# Get user input for city
print("Please enter the city name exactly as it appears in the GAUL database.")
print("Example format: 'Delhi', 'Mumbai', 'Chennai', 'Kolkata'")
city_name = input("Enter city name: ")

# Define the AOI as the boundary of the selected city
admin_boundaries = ee.FeatureCollection('FAO/GAUL/2015/level2')
city_boundary = admin_boundaries.filter(ee.Filter.eq('ADM2_NAME', city_name))
aoi = city_boundary.geometry()

# Verify if the city was found
if city_boundary.size().getInfo() == 0:
    raise ValueError(f"City '{city_name}' not found in database. Please check the spelling and try again.")

# Function to apply scale factors to Landsat 8 image
def apply_scale_factors(image):
    optical_bands = image.select('SR_B.*').multiply(0.0000275).add(-0.2)
    thermal_bands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
    return image.addBands(optical_bands, None, True).addBands(thermal_bands, None, True)

# Function to mask clouds in Landsat 8 images
def mask_l8sr(image):
    cloud_shadow_bit_mask = (1 << 3)
    clouds_bit_mask = (1 << 5)
    qa = image.select('QA_PIXEL')
    mask = qa.bitwiseAnd(cloud_shadow_bit_mask).eq(0).And(qa.bitwiseAnd(clouds_bit_mask).eq(0))
    return image.updateMask(mask)

# Function to calculate Land Surface Temperature (LST)
def calculate_lst(image):
    # Calculate NDVI
    ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')

    # Calculate emissivity
    em = ndvi.expression(
        '(NDVIm < 0 ? 0.985 : (NDVIm > 0.7 ? 0.99 : 0.985 + 0.005 * NDVIm))', {
        'NDVIm': ndvi
    }).rename('EM')

    # Get thermal band
    thermal = image.select('ST_B10').rename('thermal')

    # Calculate LST
    lst = thermal.expression(
        '(TB / (1 + (0.00115 * (TB / 1.438)) * log(EM))) - 273.15', {
            'TB': thermal,
            'EM': em
    }).rename('LST')

    return lst

# Function to get image collection for a specific year
def get_image_collection(year):
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'

    collection = (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        .filterDate(start_date, end_date)
        .filterBounds(aoi)
        .map(apply_scale_factors)
        .map(mask_l8sr))

    # Check if collection is empty
    if collection.size().getInfo() == 0:
        raise ValueError(f"No Landsat 8 images found for {city_name} in {year}")

    return collection

# Create a Folium map centered on the city
city_center = aoi.centroid().coordinates().getInfo()
Map = folium.Map(location=[city_center[1], city_center[0]], zoom_start=11)

# Add base layer
folium.TileLayer(
    tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attr='OpenStreetMap',
    name='OpenStreetMap',
    overlay=False,
    control=True
).add_to(Map)

# Process each year
years = ['2019', '2020', '2021', '2022', '2023']
lst_values = {}

# Visualization parameters
lst_vis = {
    'min': 25,
    'max': 50,
    'palette': [
        '#040274', '#040281', '#0502a3', '#0502b8', '#0502ce', '#0502e6',
        '#0602ff', '#235cb1', '#307ef3', '#269db1', '#30c8e2', '#32d3ef',
        '#3be285', '#3ff38f', '#86e26f', '#3ae237', '#b5e22e', '#d6e21f',
        '#fff705', '#ffd611', '#ffb613', '#ff8b13', '#ff6e08', '#ff500d',
        '#ff0000', '#de0101', '#c21301', '#a71001', '#911003'
    ],
    'opacity': 0.3
}

def add_ee_layer(image, vis_params, name):
    map_id_dict = ee.Image(image).getMapId(vis_params)
    folium.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        name=name,
        overlay=True,
        control=True
    ).add_to(Map)

# Process each year
for year in years:
    try:
        print(f"\nProcessing year: {year}")
        collection = get_image_collection(year)

        # Get median image for the year
        median_image = collection.median()

        # Calculate LST
        lst_image = calculate_lst(median_image).clip(aoi)

        # Calculate mean LST
        lst_mean = lst_image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=30,
            maxPixels=1e9
        ).get('LST').getInfo()

        lst_values[year] = lst_mean
        print(f"Mean LST for {year}: {lst_mean:.2f}°C")

        # Add layer to map
        add_ee_layer(lst_image, lst_vis, f'LST {year}')

    except Exception as e:
        print(f"Error processing year {year}: {str(e)}")
        lst_values[year] = None

# Add layer control
folium.LayerControl().add_to(Map)

# Generate analysis using Gemini if we have valid data
if any(lst_values.values()):
    # Calculate additional statistics
    valid_temps = [v for v in lst_values.values() if v is not None]
    if valid_temps:
        max_temp = max(valid_temps)
        min_temp = min(valid_temps)
        avg_temp = sum(valid_temps) / len(valid_temps)
        temp_range = max_temp - min_temp

        # Calculate year-over-year changes
        changes = []
        years_list = list(lst_values.keys())
        for i in range(1, len(years_list)):
            if lst_values[years_list[i]] is not None and lst_values[years_list[i-1]] is not None:
                change = lst_values[years_list[i]] - lst_values[years_list[i-1]]
                changes.append(change)

    # Create temperature data string
    temp_data = []
    for year in years:
        if lst_values[year] is not None:
            temp_data.append(f"- {year}: {lst_values[year]:.2f}°C")
        else:
            temp_data.append(f"- {year}: No data available")
    temp_data_str = "\n".join(temp_data)

    # Create changes string
    changes_str = ", ".join([f"{change:+.2f}°C" for change in changes])

# Display the map
Map
