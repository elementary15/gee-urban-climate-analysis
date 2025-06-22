A comprehensive Python toolkit for analyzing urban climate patterns using Google Earth Engine and Landsat 8 satellite data. This repository provides ready-to-use scripts for Land Surface Temperature (LST) analysis, vegetation density mapping, and surface albedo calculations with interactive visualizations.
Features
Land Surface Temperature Analysis

Multi-year LST calculation using Landsat 8 thermal infrared data
NDVI-based emissivity estimation
Cloud masking and quality filtering
Temporal trend analysis (2019-2023)
Statistical summary generation

Vegetation & Albedo Analysis

NDVI-based vegetation density classification
Multi-band surface albedo calculation
Long-term temporal analysis (2015-2023)
Interactive map visualization with custom legends
Comprehensive statistical reporting

Visualization & Export

Interactive Folium maps with multiple layers
Custom legends and compass rose
HTML export for web sharing
Statistical trend analysis
Professional map styling

Sample Outputs
The toolkit generates interactive maps showing:

Temperature Hotspots: Urban heat island patterns and intensity
Vegetation Density: Green space distribution and changes over time
Surface Reflectance: Albedo patterns affecting local climate
Temporal Trends: Multi-year changes in urban climate indicators

Installation
Prerequisites

Python 3.7 or higher
Google Earth Engine account (sign up here)
Google Colab account (optional, for cloud execution)

The analysis supports any city available in the FAO GAUL 2015 Level 2 administrative boundaries database. Common examples include:
India: Delhi, Mumbai, Chennai, Kolkata, Bengaluru, Hyderabad, Ahmedabad, Pune, Surat, Jaipur
Global: Most major metropolitan areas worldwide
Note: City names must match exactly as they appear in the GAUL database.
🔬 Technical Details
Data Sources

Landsat 8 Collection 2 Level 2: Surface reflectance and surface temperature
FAO GAUL 2015: Administrative boundaries for area definition
Quality Assessment: Cloud and cloud shadow masking using QA_PIXEL band

Algorithms

LST Calculation: Single-channel algorithm with NDVI-based emissivity
Vegetation Classification: NDVI thresholding (Low: <0.2, Medium: 0.2-0.5, High: >0.5)
Albedo Calculation: Multi-band approach using Liang et al. (2001) coefficients

Processing Parameters

Spatial Resolution: 30m (Landsat 8 native resolution)
Temporal Coverage: 2013-present (Landsat 8 operational period)
Cloud Filtering: <20% cloud cover threshold
Scale: Regional to city-wide analysis
