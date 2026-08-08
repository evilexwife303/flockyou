import geopandas as gpd
import pandas as pd
import os

def run_spatial_intersection():
    print("=== STARTING MASTER SPATIAL INTERSECTION ===")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.join(script_dir, "../data/raw")
    proc_dir = os.path.join(script_dir, "../data/processed")
    os.makedirs(proc_dir, exist_ok=True)
    
    print("Loading raw GeoJSON files...")
    cameras = gpd.read_file(os.path.join(raw_dir, "alpr_cameras.geojson"))
    sites = gpd.read_file(os.path.join(raw_dir, "sensitive_sites.geojson"))
    
    census_file = os.path.join(raw_dir, "sacramento_census_blockgroups.geojson")
    if not os.path.exists(census_file):
        census_file = os.path.join(raw_dir, "sacramento_census_tracts.geojson")
    census = gpd.read_file(census_file)

    print("Projecting maps to CA Albers (Meters)...")
    cameras_proj = cameras.to_crs("EPSG:3310")
    sites_proj = sites.to_crs("EPSG:3310")
    census_proj = census.to_crs("EPSG:3310")

    sites_proj.rename(columns={'name': 'site_name', 'category': 'site_category'}, inplace=True)

    print("Intersecting Cameras with Demographics...")
    cameras_with_demographics = gpd.sjoin(cameras_proj, census_proj, how="left", predicate="intersects")
    cameras_with_demographics.drop(columns=['index_right'], inplace=True, errors='ignore')

    print("Casting 45-meter capture cones around cameras...")
    camera_cones = cameras_with_demographics.copy()
    camera_cones['geometry'] = camera_cones.geometry.buffer(45)

    print("Scanning capture cones for sensitive infrastructure...")
    surveilled_sites = gpd.sjoin(sites_proj, camera_cones, how="inner", predicate="within")

    if not surveilled_sites.empty:
        site_summary = surveilled_sites.groupby('index_right').agg(
            surveilled_sites_count=('site_name', 'count'),
            surveilled_sites_list=('site_name', lambda x: ', '.join(x.dropna().astype(str).unique())),
            surveilled_categories=('site_category', lambda x: ', '.join(x.dropna().astype(str).unique()))
        ).reset_index()
    else:
        site_summary = pd.DataFrame(columns=['index_right', 'surveilled_sites_count', 'surveilled_sites_list', 'surveilled_categories'])

    site_summary.rename(columns={'index_right': 'index'}, inplace=True)
    cameras_with_demographics = cameras_with_demographics.reset_index().merge(
        site_summary, on='index', how='left'
    )
    
    cameras_with_demographics['surveilled_sites_count'] = cameras_with_demographics['surveilled_sites_count'].fillna(0).astype(int)
    cameras_with_demographics['surveilled_sites_list'] = cameras_with_demographics['surveilled_sites_list'].fillna("None")
    cameras_with_demographics['surveilled_categories'] = cameras_with_demographics['surveilled_categories'].fillna("None")

    print("Normalizing demographic variables...")
    
    numeric_cols = [
        'pop_total', 'poverty_universe', 'pop_poverty', 'pop_non_citizen', 
        'pop_black', 'pop_hispanic', 'total_households', 'renter_occupied', 'median_income'
    ]
    
    # Scrub all negative Census suppression flags before doing any math
    for col in numeric_cols:
        if col in cameras_with_demographics.columns:
            cameras_with_demographics[col] = pd.to_numeric(cameras_with_demographics[col], errors='coerce')
            cameras_with_demographics[col] = cameras_with_demographics[col].apply(lambda x: None if pd.notnull(x) and x < 0 else x)
    
    # Establish correct statistical denominators
    pop = cameras_with_demographics['pop_total'].replace(0, 1) 
    pov_univ = cameras_with_demographics['poverty_universe'].replace(0, 1) 
    households = cameras_with_demographics['total_households'].replace(0, 1) 
    
    # Calculate mathematically sound percentages
    cameras_with_demographics['pct_poverty'] = (cameras_with_demographics['pop_poverty'] / pov_univ) * 100
    cameras_with_demographics['pct_renter'] = (cameras_with_demographics['renter_occupied'] / households) * 100
    cameras_with_demographics['pct_non_citizen'] = (cameras_with_demographics['pop_non_citizen'] / pop) * 100
    cameras_with_demographics['pct_black'] = (cameras_with_demographics['pop_black'] / pop) * 100
    cameras_with_demographics['pct_hispanic'] = (cameras_with_demographics['pop_hispanic'] / pop) * 100

    print("Converting back to Web Mercator (EPSG:4326) for Dashboard mapping...")
    final_gdf = cameras_with_demographics.drop(columns=['index']).to_crs("EPSG:4326")
    
    output_path = os.path.join(proc_dir, "master_alpr_dragnet.geojson")
    final_gdf.to_file(output_path, driver="GeoJSON")
    
    print(f"\nSUCCESS! Master dataset ready.")
    print(f"Total ALPRs Processed: {len(final_gdf)}")
    print(f"Cameras monitoring sensitive sites: {len(final_gdf[final_gdf['surveilled_sites_count'] > 0])}")
    print(f"File saved to: {output_path}")

if __name__ == "__main__":
    run_spatial_intersection()