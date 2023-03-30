import ee
from code.metricFunctions import prepareMetrics
import pytest

# Test the initialisation with dummy inputs
def test_init():
    """Create a function to test the initialisation
      of prepareMetrics"""
    cImage = ee.Image.constant(1).addBands([ee.Image.constant(2), ee.Image.constant(3)])
    nClasses = 3
    nFolds = 3
    try:
        prepareMetrics(cImage, nClasses, nFolds)
    except TypeError:
        pytest.fail("Could not initialise prep metrics")
        

