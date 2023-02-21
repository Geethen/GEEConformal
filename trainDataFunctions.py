import ee
from covariateFunctions import prepareCovariates

class prepareTrainingData:
    def __init__(self, covariates, points, targetProperty, nFolds, nAngles, proj= 'EPSG:4326'):
        self.covariates = covariates
        self.points = points
        self.targetProperty = targetProperty
        self.nFolds = nFolds
        self.nAngles = nAngles
        self.proj = proj
        
    def _prepareCovariates(self):
        # Spatial autocorr using rotated coordinates
        steps = ee.List.sequence(0, 1, count = self.nAngles).slice(0,-1)
        steps = steps.map(lambda ang: prepareCovariates(proj = self.proj).addRotatedCoords(ang))
        steps = ee.ImageCollection(steps).toBands()
        # add the bands, rename all bands
        s2Flat = self.covariates.addBands(steps).regexpRename('^(.{0})', 'band')
        return s2Flat
        
    def _preparePoints(self):
        # add coordinates to points.
        points = prepareCovariates(proj = 'EPSG:32736').addCoordProperty(self.points)

        # cluster points into groups based on coordinates
        clusterer = ee.Clusterer.wekaKMeans(self.nFolds).train(features = points,inputProperties = ['x','y'])
        points = points.cluster(clusterer)
        return points
    
    def covariatesToPoints(self):
        # Extract image values at points
        allData = self._prepareCovariates().reduceRegions(collection = self._preparePoints(),
                                       reducer = ee.Reducer.first(),
                                       scale = 10,
                                       tileScale = 8)
        return allData