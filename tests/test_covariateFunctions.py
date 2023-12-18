import ee
import pytest
from code.covariateFunctions import prepareCovariates

# encode json key file in linux (colab)
# !cat secrets.json | base64 | tr -d '\n' > secrets.b64
# test using this command
# import ee
# service_account = 'geethen.singh@gmail.com'
# credentials = ee.ServiceAccountCredentials(service_account, 'secrets.json')
# ee.Initialize(credentials)

service_account = 'github-action@ee-geethensingh.iam.gserviceaccount.com'
credentials = ee.ServiceAccountCredentials(service_account, 'secret.json')
ee.Initialize(credentials)

#  Test the initialisation works
def test_init():
    covariates = ee.Image("LANDSAT/LC08/C01/T1_SR/LC08_044034_20140318")
    proj = 'EPSG:4326'
    nAngles = 10
    try:
        prep = prepareCovariates(covariates, proj, nAngles)
    except ValueError:
        pytest.fail("prepareCovariates raised ValueError and Failed to initisalise")

# test_addRotatedCoords Tests if given an angle a band is returned
def test_addRotatedCoords():
    ang = 0.2
    covariates = ee.Image("LANDSAT/LC08/C01/T1_SR/LC08_044034_20140318")
    proj = 'EPSG:4326'
    nAngles = 10
    prep = prepareCovariates(covariates, proj, nAngles)
    try:
        len(prep._addRotatedCoords(ang).bandNames().getInfo())==1
    except ValueError:
        pytest.fail("_addRotatedCovariates() does not add only 1 band")

# Tests if number of bands is equal to the number of covariate bands + nAngle bands
def test_addRotatedCoords2():
    ang = 0.2
    covariates = ee.Image("LANDSAT/LC08/C01/T1_SR/LC08_044034_20140318").select('B1')
    proj = 'EPSG:4326'
    nAngles = 10
    prep = prepareCovariates(covariates, proj, nAngles)
    try:
        nBands = len(prep.addRotatedCoords().bandNames().getInfo())
        nBands==11
    except ValueError:
        pytest.fail(f"addRotatedCovariates() adds incorrect number of band. Meant to have 6 bands but has {nBands}")

#  Tests if number of bands is equal to the number of covariate bands + 5 topo bands
def test_addTopoBands():
    ang = 0.2
    covariates = ee.Image("LANDSAT/LC08/C01/T1_SR/LC08_044034_20140318").select('B1')
    proj = 'EPSG:4326'
    nAngles = 10
    prep = prepareCovariates(covariates, proj, nAngles)
    try:
        nBands = len(prep.addTopoBands().bandNames().getInfo())
        nBands==6
    except ValueError:
        pytest.fail(f"addTopoBands() adds incorrect number of bands. Meant to have 6 bands but has {nBands}")

# Tests that the addcovariates function handles invalid arguments correctly. tags: [edge case]
def test_addCovariates_invalid():
    # Edge case test for adding covariates with invalid arguments
    covariates = ee.Image("LANDSAT/LC08/C01/T1_SR/LC08_044034_20140318")
    proj = 'EPSG:4326'
    nAngles = 10
    prep = prepareCovariates(covariates, proj, nAngles)
    try:
        prep.addCovariates(rotatedCoords="True", topoBands="True")
    except TypeError:
        pytest.fail("addCovariates() raised TypeError unexpectedly!")
