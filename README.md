Farmlytics QGIS Plugin
======================

Overview
--------
Farmlytics is a QGIS plugin that enables interactive analysis and visualization of NDVI (Normalized Difference Vegetation Index) time-series, crop cycles, and phenological information for farm plots within a GIS project. With Farmlytics, you can select farm features on a vector layer, view detailed time-series charts, examine cycles and peaks, and compare multiple farms—all within a modern, export-friendly PyQt interface.

Features
--------
- Interactive NDVI trend plotting for selected farm plots, auto-highlighting planting (SOS), harvest (EOS), and peak events.
- Attribute table display with dynamic extraction of cycles, stats, and phenological dates for each farm.
- Multi-farm comparison: select multiple farms and view their NDVI series as overlays on a single interactive plot.
- Export functions: save plots as PNG/JPEG/PDF/SVG and tables as CSV.
- Visual controls for date filtering, farm selection, and plot visibility.
- Integrated with QGIS, using PyQt5 and matplotlib for a seamless user experience.

Installation
------------
1. Copy the plugin folder (containing Farmlytics.py and resources) to your QGIS plugin directory:
   - Windows:  %USERPROFILE%\.qgis2\python\plugins\
   - Mac/Linux: ~/.qgis2/python/plugins/
2. Restart QGIS.
3. Enable Farmlytics via the Plug-in Manager.

Usage
-----
1. Load a vector layer containing farm plots, with properly formatted NDVI and date attributes.
2. Click the Farmlytics toolbar icon or choose it from the QGIS Plugins menu.
3. When prompted, select the target farm layer.
4. Click a farm feature on the map to open its detail dialog.
5. Use on-screen controls to explore NDVI plots, review cycles and phenological stats, use date filtering, and compare farms.
6. Export graphs and tables using the built-in export buttons.

Data Requirements
-----------------
The plugin expects the following attribute structure in your vector layer features:
- General fields: 'Farm_ID', 'crop', 'Area', 'harvest_date'
- Multiple cycles per farm (attributes for each: Cycle1, Cycle2, ..., CycleN):
  - 'Cycle#_SOS'
  - 'Cycle#_EOS'
  - 'Cycle#_Duration'
  - 'Cycle#_Peak NDVI'
  - 'Cycle#_Peak date'
- NDVI time-series:
  - 'Datetime'   (e.g., "2023-04-12,2023-04-19,...")
  - 'Mean NDVI'  (e.g., "0.32,0.42,...")

The plugin is preconfigured to handle up to 3 cycles per farm but can be extended for more cycles if needed.

Dependencies
------------
- QGIS 3.x
- PyQt5
- matplotlib
- pandas
- (optional) plotly

File Structure
--------------
- Farmlytics.py       # Main plugin implementation
- icon.png            # Toolbar and menu icon
- (Other resources or Python modules as needed)

Customization & Notes
---------------------
- Plot font sizes and formatting are set in the plotting functions. Adjust them for different screen resolutions or dialog sizes as needed.
- Extendable: add further analysis, more cycles, or alternative plot types by building on the code base.
- Make sure input fields in your layer are present and consistently named.

Troubleshooting
---------------
- If plots don't appear, verify your data layer contains properly formatted dates and NDVI fields.
- If the plugin fails to load, check that all Python package dependencies are installed and activated in your QGIS environment.
- For GUI or export issues, watch the QGIS Python console for tracebacks or error information.

License & Contact
-----------------
This plugin is provided "as-is" for non-commercial academic and internal use. For commercial/redistribution use, please contact the author.

Author: Mahathi S
Contact: mahathisarp@gmail.com
Created: August 2025

Enjoy efficient farm NDVI analytics in QGIS with Farmlytics!
=======
