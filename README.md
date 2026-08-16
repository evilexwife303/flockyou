# FlockYou: Spatial Dragnet Analysis

**[📍 View the Live Interactive Dashboard Here](https://evilexwife303.github.io/flockyou/)**

An open-source geospatial dashboard mapping the physical intersection of Automated License Plate Readers (ALPR) and sensitive community infrastructure.

This project was initially built to analyze the surveillance footprint in Sacramento, California. I wanted to identify cameras whose 45-meter visual dragnets directly intercept healthcare clinics, legal aid offices, and community centers.

## Features

* **Spatial Intersection:** Calculates direct line-of-sight privacy risks between ALPR cameras and mapped sensitive facilities.
* **Interactive Dragnet Cones:** Visualizes the exact 60° horizontal field of view and 45-meter range of each camera.
* **Google Street View Integration:** Forces Google Maps to drop a pin at the exact camera coordinates and perfectly rotate the camera pitch/heading to recreate the surveillance perspective.
* **Demographic Context:** Integrates live ESRI ArcGIS reverse-geocoding and localized census data to evaluate the socioeconomic context of the surveillance zone.

## Build Your Own City's Dashboard

This dashboard is designed to be highly portable. You do not need to rewrite the JavaScript to map your own city. 

1. **Fork this repository** to your own GitHub account.
2. Replace the `.geojson` files inside the `public/data/` folder with your own local spatial data:
   * `master_alpr_dragnet.geojson` (Your camera locations and headings)
   * `sensitive_sites.geojson` (Your mapped infrastructure points)
   * `census_data.geojson` (If using a local static file for demographics, swap this with your local census tracts)
3. The dashboard will dynamically ingest your files and generate a new interface for your city.

## Running Locally

To test the dashboard on your own machine without triggering browser CORS errors, spin up a local Python server:

```bash
cd public
python -m http.server 8000