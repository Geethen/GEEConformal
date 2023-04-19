import ee
import pytest
from code.timeSeriesFunctions import prepareTS

# test prepareTS init
def test_init_prepareTS():
    # Start and end dates for time series
    Date_Start = ee.Date('2017-01-01')
    Date_End = ee.Date('2017-12-31')
    # how many days to summarise in each image e.g 30 days = 12 images per year
    day_int = 30 #step size
    # cloud probabillity threshold
    CLOUD_THRESH=30
    # which bands to keep
    BANDS = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6','B7', 'B8', 'B8A', 'B9', 'B11','B12', 'ndvi','ndwi','ndre','nbr','evi']
    # Point of interest (in this case, a point in South Africa)
    aoi = ee.Geometry.Point([25.181, -28.490])
    try:
        # add cloud probability band to sentinel-2, compute a composite image for interval (day_int), and perform gap filling.
        test = prepareTS(Date_Start,Date_End,day_int,aoi,CLOUD_THRESH,BANDS)
    except ValueError:
        pytest.fail(f"Failed to initialize prepareTS")

# test create s2 mosaic
def test_init_prepares21cTS():
    # Start and end dates for time series
    Date_Start = ee.Date('2017-01-01')
    Date_End = ee.Date('2017-12-31')
    # how many days to summarise in each image e.g 30 days = 12 images per year
    day_int = 30 #step size
    # cloud probabillity threshold
    CLOUD_THRESH=30
    # which bands to keep
    BANDS = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6','B7', 'B8', 'B8A', 'B9', 'B11','B12', 'ndvi','ndwi','ndre','nbr','evi']
    # Point of interest (in this case, a point in South Africa)
    aoi = ee.Geometry.Point([25.181, -28.490])
    try:
        # add cloud probability band to sentinel-2, compute a composite image for interval (day_int), and perform gap filling.
        test = prepareTS(Date_Start,Date_End,day_int,aoi,CLOUD_THRESH,BANDS).timeSeries(satellite = 'S2', s2_level = 1)
    except ValueError:
        pytest.fail(f"Failed to prepare a Sentinel-2, level 1C time series")
    
    # test create s2 mosaic
def test_init_prepares22aTS():
    # Start and end dates for time series
    Date_Start = ee.Date('2017-01-01')
    Date_End = ee.Date('2017-12-31')
    # how many days to summarise in each image e.g 30 days = 12 images per year
    day_int = 30 #step size
    # cloud probabillity threshold
    CLOUD_THRESH=30
    # which bands to keep
    BANDS = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6','B7', 'B8', 'B8A', 'B9', 'B11','B12', 'ndvi','ndwi','ndre','nbr','evi']
    # Point of interest (in this case, a point in South Africa)
    aoi = ee.Geometry.Point([25.181, -28.490])
    try:
        # add cloud probability band to sentinel-2, compute a composite image for interval (day_int), and perform gap filling.
        test = prepareTS(Date_Start,Date_End,day_int,aoi,CLOUD_THRESH,BANDS).timeSeries(satellite = 'S2', s2_level = 2)
    except ValueError:
        pytest.fail(f"Failed to prepare a Sentinel-2, level 2A time series")
    

# test create s1 mosaic
def test_init_prepares1TS():
    # Start and end dates for time series
    Date_Start = ee.Date('2017-01-01')
    Date_End = ee.Date('2017-12-31')
    # how many days to summarise in each image e.g 30 days = 12 images per year
    day_int = 30 #step size
    # cloud probabillity threshold
    CLOUD_THRESH=30
    # which bands to keep
    BANDS = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6','B7', 'B8', 'B8A', 'B9', 'B11','B12', 'ndvi','ndwi','ndre','nbr','evi']
    # Point of interest (in this case, a point in South Africa)
    aoi = ee.Geometry.Point([25.181, -28.490])
    try:
        # add cloud probability band to sentinel-2, compute a composite image for interval (day_int), and perform gap filling.
        test = prepareTS(Date_Start,Date_End,day_int,aoi,CLOUD_THRESH,BANDS).timeSeries(satellite = 'S1')
    except ValueError:
        pytest.fail(f"Failed to prepare a Sentinel-1 time series")

# test create s1 mosaic
def test_init_prepares1s21cTS():
    # Start and end dates for time series
    Date_Start = ee.Date('2017-01-01')
    Date_End = ee.Date('2017-12-31')
    # how many days to summarise in each image e.g 30 days = 12 images per year
    day_int = 30 #step size
    # cloud probabillity threshold
    CLOUD_THRESH=30
    # which bands to keep
    BANDS = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6','B7', 'B8', 'B8A', 'B9', 'B11','B12', 'ndvi','ndwi','ndre','nbr','evi']
    # Point of interest (in this case, a point in South Africa)
    aoi = ee.Geometry.Point([25.181, -28.490])
    try:
        # add cloud probability band to sentinel-2, compute a composite image for interval (day_int), and perform gap filling.
        test = prepareTS(Date_Start,Date_End,day_int,aoi,CLOUD_THRESH,BANDS).timeSeries(satellite = 'S1S2', s2_level = 1)
    except ValueError:
        pytest.fail(f"Failed to prepare a combined Sentinel-1 and Sentinel-2, level 1C time series")

# test create s1 mosaic
def test_init_prepares1s22aTS():
    # Start and end dates for time series
    Date_Start = ee.Date('2017-01-01')
    Date_End = ee.Date('2017-12-31')
    # how many days to summarise in each image e.g 30 days = 12 images per year
    day_int = 30 #step size
    # cloud probabillity threshold
    CLOUD_THRESH=30
    # which bands to keep
    BANDS = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6','B7', 'B8', 'B8A', 'B9', 'B11','B12', 'ndvi','ndwi','ndre','nbr','evi']
    # Point of interest (in this case, a point in South Africa)
    aoi = ee.Geometry.Point([25.181, -28.490])
    try:
        # add cloud probability band to sentinel-2, compute a composite image for interval (day_int), and perform gap filling.
        test = prepareTS(Date_Start,Date_End,day_int,aoi,CLOUD_THRESH,BANDS).timeSeries(satellite = 'S1S2', s2_level = 2)
    except ValueError:
        pytest.fail(f"Failed to prepare a Sentinel-1 and Sentinel-2, level 2A time series")
    