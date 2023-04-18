import ee
import pytest
from code.trainDataFunctions import prepareTrainingData

# Tests initialisation of prepare Training Data class
def test_init():
    covariates = ee.Image("LANDSAT/LC08/C01/T1_SR/LC08_044034_20140318")
    points = ee.FeatureCollection.randomPoints(covariates.geometry(), 10, 42, 1000).map(lambda ft: ft.set('target', 1))
    targetProperty = 'target'
    nFolds = 10
    try:
        prepareTrainingData(covariates=covariates, points= points, targetProperty = targetProperty, nFolds=nFolds)
    except ValueError:
        pytest.fail("prepareTrainingData raised ValueError and Failed to initisalise")
    

# Check if x and y coordinate properties have been attached
def test_addCoordProperty():
    covariates = ee.Image("LANDSAT/LC08/C01/T1_SR/LC08_044034_20140318")
    points = ee.FeatureCollection.randomPoints(covariates.geometry(), 10, 42, 1000).map(lambda ft: ft.set('target', 1))
    targetProperty = 'target'
    nFolds = 10
    test = prepareTrainingData(covariates=covariates, points= points, targetProperty = targetProperty, nFolds=nFolds)
    wCoords = test.addCoordProperty(points)
    try:
        # check if x and y is in list of propertyNames
        all(x in wCoords.propertyNames().getInfo() for x in ['x','y'])
    except ValueError:
        pytest.fail("x and y properties have not been added successfully")

# Check if points are being clustered -checks to see if there is a cluster attribute
def test_preparePoints():
    covariates = ee.Image("LANDSAT/LC08/C01/T1_SR/LC08_044034_20140318")
    points = ee.FeatureCollection.randomPoints(covariates.geometry(), 10, 42, 1000).map(lambda ft: ft.set('target', 1))
    targetProperty = 'target'
    nFolds = 10
    test = prepareTrainingData(covariates=covariates, points= points, targetProperty = targetProperty, nFolds=nFolds)
    wCluster = test._preparePoints()
    try:
        # check if cluster property is in list of propertyNames
        'cluster' in wCluster.propertyNames().getInfo()
    except ValueError:
        pytest.fail("Cluster property has not been added successfully")

# Check if image attributes have been extracted - checks the number of properties
def test_covariatesToPoints():
    covariates = ee.Image("LANDSAT/LC08/C01/T1_SR/LC08_044034_20140318").select('B1')
    points = ee.FeatureCollection.randomPoints(covariates.geometry(), 10, 42, 1000).map(lambda ft: ft.set('target', 1))
    targetProperty = 'target'
    nFolds = 10
    test = prepareTrainingData(covariates=covariates, points= points, targetProperty = targetProperty, nFolds=nFolds)
    data = test.covariatesToPoints()
    # should include 3 properties (target, cluster and SR_B1)
    try:
        len(data.propertyNames().getInfo())>3
    except ValueError:
        pytest.fail("Cluster property has not been added successfully")
