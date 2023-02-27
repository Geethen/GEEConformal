# Invasive_Species_Mapping
A workflow that uses time series satellite data (Sentinel-1, Sentinel-2 L1C and/or Sentinel-2 L2A) and Google Earth Engine to map invasive tree species.

This workflow involves 8-steps to install and import packages, prepare the dataset for model fitting, model evaluation and export. 

For the [end-to-end example provided](https://github.com/Geethen/Invasive_Species_Mapping/blob/main/example_usuage/end_to_end_example.ipynb), the reference points (shapefile) is already uploaded to Google Earth Engine (GEE). However, if you need to upload your shapefile to GEE you could either [manually upload it](https://developers.google.com/earth-engine/guides/table_upload) or you could upload it by using the geeup package. An example using the geeup package can be found [here](https://github.com/Geethen/Invasive_Species_Mapping/blob/main/example_usuage/geeup_Simple_CLI_for_Earth_Engine_Uploads.ipynb).
