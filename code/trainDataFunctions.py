import ee

class prepareTrainingData:
    def __init__(self, covariates, points, targetProperty, nFolds, proj= 'EPSG:4326'):
        self.covariates = covariates
        self.points = points
        self.targetProperty = targetProperty
        self.nFolds = nFolds
        self.proj = proj

    def addCoordProperty(self, features):
        """
        This function adds coordinates to the points
        """
        def coords(feature):
            return feature.geometry().transform(proj = self.proj).coordinates()

        return features.map(lambda ft: ft.set('x', coords(ft).getNumber(0)).set('y', coords(ft).getNumber(1)))
        
    def _preparePoints(self):
        # add coordinates to points.
        points = self.addCoordProperty(self.points)

        # cluster points into groups based on coordinates
        clusterer = ee.Clusterer.wekaKMeans(self.nFolds).train(features = points,inputProperties = ['x','y'])
        points = points.cluster(clusterer)
        return points
    
    def covariatesToPoints(self):
        # Extract image values at points
        allData = self.covariates.reduceRegions(collection = self._preparePoints(),
                                       reducer = ee.Reducer.first(),
                                       scale = 10,
                                       tileScale = 8)
        return allData