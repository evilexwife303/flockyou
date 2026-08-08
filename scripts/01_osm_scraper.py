import requests
import pandas as pd
import geopandas as gpd
import os

def fetch_alpr_data():
    print("Querying Overpass API for Sacramento County ALPRs...")
    
    # 1. Define the Overpass QL query
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = """
    [out:json][timeout:50];
    area["name"="Sacramento County"]["admin_level"="6"]->.searchArea;
    (
      node["man_made"="surveillance"]["surveillance:type"="ALPR"](area.searchArea);
    );
    out body;
    """

    # 2. Ping the API (UPDATED TO BYPASS 406 ERROR)
    # We add a polite User-Agent so the server doesn't block us as a bot
    headers = {
        'User-Agent': 'FlockAccountabilityProject/1.0 (Academic Research)'
    }
    
    # Switched to a POST request to safely handle the query text
    response = requests.post(overpass_url, data={'data': overpass_query}, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: API returned status code {response.status_code}")
        print(f"Server response: {response.text}")
        return
        
    data = response.json()
    
    # 3. Parse JSON into structured list
    camera_list = []
    for element in data.get('elements', []):
        if element['type'] == 'node':
            tags = element.get('tags', {})
            direction = tags.get('camera:direction', tags.get('direction', None))
            
            camera_list.append({
                'id': element['id'],
                'lat': element['lat'],
                'lon': element['lon'],
                'direction': direction,
                'operator': tags.get('operator', 'Unknown'),
                'brand': tags.get('brand', 'Unknown')
            })

    # 4. Convert to Pandas DataFrame
    df = pd.DataFrame(camera_list)
    print(f"Found {len(df)} total ALPR nodes.")

    if len(df) == 0:
        print("No cameras found. Check query parameters or network connection.")
        return

    # 5. Clean Data (Drop missing directions, coerce to numeric)
    df = df.dropna(subset=['direction']).copy()
    df['direction'] = pd.to_numeric(df['direction'], errors='coerce')
    df = df.dropna(subset=['direction'])
    
    print(f"Retained {len(df)} nodes with valid directional headings.")

    # 6. Convert to Spatial GeoDataFrame
    cameras_gdf = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df.lon, df.lat),
        crs="EPSG:4326"
    )

    # 7. Ensure output directory exists and save file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "../data/raw")
    os.makedirs(output_dir, exist_ok=True)
    
    absolute_output_path = os.path.join(output_dir, "alpr_cameras.geojson")
    cameras_gdf.to_file(absolute_output_path, driver="GeoJSON")
    print(f"Success! Raw spatial data saved to: {absolute_output_path}")

if __name__ == "__main__":
    fetch_alpr_data()