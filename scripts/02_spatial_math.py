import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
import math
import os

def create_capture_cone(point, bearing, radius=45, fov=45):
    """
    Casts a 2D geometric cone representing a Flock camera's physical capture zone.
    radius: 45 meters (approx 150 feet maximum effective ALPR range)
    fov: 45 degrees (focused optical width covering 1-2 traffic lanes)
    """
    x0, y0 = point.x, point.y
    
    # 1. Convert Compass Bearing to Standard Math Angle
    # Compass: 0=North, 90=East. Math: 0=East, 90=North.
    math_angle_deg = 90 - bearing
    
    # 2. Define the left and right boundaries of the camera's vision
    start_angle_deg = math_angle_deg - (fov / 2)
    end_angle_deg = math_angle_deg + (fov / 2)
    
    # 3. Build the Polygon vertices starting at the pole
    vertices = [(x0, y0)] 
    
    # Draw the curved outer edge of the capture zone using trigonometry
    current_angle = start_angle_deg
    while current_angle <= end_angle_deg:
        angle_rad = math.radians(current_angle)
        x = x0 + radius * math.cos(angle_rad)
        y = y0 + radius * math.sin(angle_rad)
        vertices.append((x, y))
        current_angle += 5 # Plot a point every 5 degrees for a smooth arc
        
    # Close the shape by returning to the origin pole
    vertices.append((x0, y0))
    
    return Polygon(vertices)

def build_spatial_cones():
    print("Loading raw ALPR point data...")
    
    # Define file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, "../data/raw/alpr_cameras.geojson")
    output_dir = os.path.join(script_dir, "../data/processed")
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Load the data
    gdf = gpd.read_file(input_path)
    
    # 2. CRITICAL STEP: Reproject to the Sacramento Regional Metric Grid
    # EPSG:6424 projects the curved earth onto a flat 2D grid in meters for Central California.
    gdf = gdf.to_crs("EPSG:6424")
    print("Successfully flattened map to metric grid (EPSG:6424).")
    
    # 3. Cast the capture cones
    print(f"Casting 45-meter capture cones for {len(gdf)} cameras...")
    cone_geometries = []
    
    for idx, row in gdf.iterrows():
        pt = row['geometry']
        heading = row['direction']
        
        # Pass the hardware-calibrated parameters
        cone = create_capture_cone(pt, heading, radius=45, fov=45)
        cone_geometries.append(cone)
        
    # 4. Overwrite the dot points with our new solid polygons
    gdf['geometry'] = cone_geometries
    
    # 5. Reproject back to standard GPS coordinates for web mapping compatibility
    gdf = gdf.to_crs("EPSG:4326")
    
    # 6. Save the finalized layer
    output_path = os.path.join(output_dir, "alpr_cones.geojson")
    gdf.to_file(output_path, driver="GeoJSON")
    print(f"Success! Modeled capture cones saved to: {output_path}")

if __name__ == "__main__":
    build_spatial_cones()