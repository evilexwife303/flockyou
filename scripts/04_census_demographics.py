import requests
import pandas as pd
import geopandas as gpd
import os
import zipfile
import io

def fetch_scalable_census_data(state_fips="06", county_fips="067", year="2022"):
    print(f"=== PULLING LIVE CENSUS DATA FOR FIPS {state_fips}{county_fips} ({year} ACS) ===")
    
    # 1. Added proper statistical denominators for Poverty and Households
    variables = (
        "NAME,B01003_001E,B19013_001E,B02001_002E,B02001_003E,"
        "B02001_004E,B02001_005E,B02001_006E,B02001_007E,B02001_008E,"
        "B03002_012E,B05001_006E,B17001_001E,B17001_002E,B25003_001E,B25003_003E,B23025_005E,B11005_002E"
    )
    
    api_url = f"https://api.census.gov/data/{year}/acs/acs5"
    
    params = {
        "get": variables,
        "for": "block group:*",
        "in": f"state:{state_fips} county:{county_fips} tract:*",
        "key": "99a2414bcd62c2e8acfbaead474694d97ce91e16"
    }
    
    print("Querying US Census Bureau API...")
    response = requests.get(api_url, params=params)
    
    if response.status_code != 200:
        print(f"API Error (Status {response.status_code}): {response.text}")
        return
        
    data = response.json()
    headers = data[0]
    df_demo = pd.DataFrame(data[1:], columns=headers)
    
    # 3. Rename columns to human-readable format, including our new denominators
    rename_dict = {
        'B01003_001E': 'pop_total',
        'B19013_001E': 'median_income',
        'B02001_002E': 'pop_white',
        'B02001_003E': 'pop_black',
        'B02001_004E': 'pop_native',
        'B02001_005E': 'pop_asian',
        'B02001_006E': 'pop_pacific',
        'B02001_007E': 'pop_other',
        'B02001_008E': 'pop_two_plus',
        'B03002_012E': 'pop_hispanic',
        'B05001_006E': 'pop_non_citizen',
        'B17001_001E': 'poverty_universe', 
        'B17001_002E': 'pop_poverty',
        'B25003_001E': 'total_households', 
        'B25003_003E': 'renter_occupied',
        'B23025_005E': 'unemployed',
        'B11005_002E': 'single_parent_households',
    }
    df_demo.rename(columns=rename_dict, inplace=True)
    
    df_demo['GEOID'] = df_demo['state'] + df_demo['county'] + df_demo['tract'] + df_demo['block group']
    print(f"Successfully pulled demographics for {len(df_demo)} Block Groups.")

    print("Downloading spatial boundary files from Census TIGER/Line servers...")
    shapefile_url = f"https://www2.census.gov/geo/tiger/GENZ{year}/shp/cb_{year}_{state_fips}_bg_500k.zip"
    
    r = requests.get(shapefile_url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    
    temp_dir = "temp_shapefiles"
    os.makedirs(temp_dir, exist_ok=True)
    z.extractall(temp_dir)
    
    shapefile_path = os.path.join(temp_dir, f"cb_{year}_{state_fips}_bg_500k.shp")
    gdf_boundaries = gpd.read_file(shapefile_path)
    
    gdf_county = gdf_boundaries[gdf_boundaries['COUNTYFP'] == county_fips].copy()
    
    print("Merging demographics with spatial boundaries...")
    merged_gdf = gdf_county.merge(df_demo, on='GEOID', how='inner')
    merged_gdf = merged_gdf.to_crs("EPSG:4326")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "../data/raw")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "sacramento_census_blockgroups.geojson")
    merged_gdf.to_file(output_path, driver="GeoJSON")
    print(f"Success! Scalable Census geometries saved to: {output_path}")
    
    import shutil
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    fetch_scalable_census_data(state_fips="06", county_fips="067", year="2022")