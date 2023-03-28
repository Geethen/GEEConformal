import ee
# Test the initialisation with dummy inputs
def test_init():
    """Create a function to test the initialisation
      of prepareMetrics"""
    cImage = ee.Image.Constant(1).addBands([ee.Image.Constant(2), ee.Image.Constant(3)])
    nClasses = 3
    nFolds = 3
    with pytest.raises(TypeError):
        prepareMetrics(cImage, nClasses, nFolds)

