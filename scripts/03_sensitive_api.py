import requests
import pandas as pd
import geopandas as gpd
import os

def fetch_comprehensive_sites():
    print("=== PULLING TIER 2 SENSITIVE INFRASTRUCTURE (OSM) ===")
    
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # We use 'nwr' (Node, Way, Relation) to capture both point locations AND building polygons.
    # 'out center;' ensures that large buildings are converted to a single central lat/lon coordinate.
    overpass_query = """
    [out:json][timeout:90];
    area["name"="Sacramento County"]["admin_level"="6"]->.searchArea;

    (
      // 1. Healthcare & Clinics
      nwr["amenity"="clinic"](area.searchArea);
      nwr["healthcare"="clinic"](area.searchArea);
      nwr["healthcare"="abortion"](area.searchArea);
      nwr["amenity"="hospital"](area.searchArea);
      nwr["healthcare"="birthing_center"](area.searchArea);
      
      // 2. Legal Aid, Public Defenders, & Social Infrastructure
      nwr["amenity"="social_facility"](area.searchArea);
      nwr["social_facility"="food_bank"](area.searchArea);
      nwr["office"="legal"](area.searchArea);
      nwr["office"="lawyer"](area.searchArea); 
      nwr["office"="ngo"](area.searchArea);
      nwr["office"="diplomatic"](area.searchArea); 
      nwr["office"="association"](area.searchArea);
      
      // 3. Housing Precarity
      nwr["tourism"="motel"](area.searchArea);
      
      // 4. Broad Community Hubs
      nwr["amenity"="school"](area.searchArea);
      nwr["amenity"="college"](area.searchArea);
      nwr["leisure"="fitness_centre"](area.searchArea);
      nwr["leisure"="sports_centre"](area.searchArea);
      nwr["amenity"="place_of_worship"](area.searchArea);
      nwr["amenity"="bus_station"](area.searchArea);
      nwr["railway"="station"](area.searchArea);
    );
    out center;
    """

    headers = {
        'User-Agent': 'FlockAccountabilityProject/1.0 (Academic Research)'
    }
    
    print("Querying Overpass API for comprehensive civic targets...")
    response = requests.post(overpass_url, data={'data': overpass_query}, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: API returned status code {response.status_code}")
        return
        
    data = response.json()
    
    site_list = []
    for element in data.get('elements', []):
        tags = element.get('tags', {})
        name = tags.get('name', 'Unnamed Facility')
        
        # Categorize the site
        category = (
            tags.get('amenity') or 
            tags.get('healthcare') or 
            tags.get('social_facility') or 
            tags.get('office') or 
            tags.get('tourism') or 
            tags.get('leisure') or 
            tags.get('railway') or 
            'community_hub'
        )
        
        # Extract coordinates (Nodes have lat/lon directly; Ways/Relations use 'center')
        if element['type'] == 'node':
            lat, lon = element.get('lat'), element.get('lon')
        else:
            lat, lon = element.get('center', {}).get('lat'), element.get('center', {}).get('lon')
            
        if lat and lon:
            site_list.append({
                'id': element['id'],
                'name': name,
                'category': category,
                'lat': lat,
                'lon': lon,
                'source': 'OSM_Tier_2'
            })

    df_sites = pd.DataFrame(site_list)
    print(f"Successfully pulled {len(df_sites)} public and community sites from OSM.")

    # ==========================================
    # TIER 3 OVERRIDE: INJECT CUSTOM SITES CSV
    # ==========================================
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_data_dir = os.path.join(script_dir, "../data/raw")
    private_csv_path = os.path.join(raw_data_dir, "tier3_private_sites.csv")
    
    if os.path.exists(private_csv_path):
        print(f"Detected custom locations CSV. Merging sites...")
        df_private = pd.read_csv(private_csv_path)
        
        # Ensure the CSV has 'name', 'category', 'lat', 'lon'
        if all(col in df_private.columns for col in ['name', 'category', 'lat', 'lon']):
            df_private['source'] = 'Custom_Tier_3'
            # Give them a dummy ID if missing
            if 'id' not in df_private.columns:
                df_private['id'] = range(9000000, 9000000 + len(df_private)) 
            
            df_sites = pd.concat([df_sites, df_private], ignore_index=True)
            print(f"Merged {len(df_private)} custom sites into the dataset.")
        else:
            print("Warning: tier3_private_sites.csv is missing required columns (name, category, lat, lon). Skipping merge.")
    else:
        print("No tier3_private_sites.csv found in data/raw/. Proceeding with OSM public data only.")

    # Convert to Spatial GeoDataFrame (EPSG:4326)
    sites_gdf = gpd.GeoDataFrame(
        df_sites, 
        geometry=gpd.points_from_xy(df_sites.lon, df_sites.lat),
        crs="EPSG:4326"
    )

    # Save to raw data folder
    os.makedirs(raw_data_dir, exist_ok=True)
    output_path = os.path.join(raw_data_dir, "sensitive_sites.geojson")
    
    sites_gdf.to_file(output_path, driver="GeoJSON")
    print(f"SUCCESS! Master locations file saved to: {output_path}")

if __name__ == "__main__":
    fetch_comprehensive_sites()