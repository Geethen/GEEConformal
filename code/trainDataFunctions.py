import ee

class prepareTrainingData:
    """This class prepares training data for machine learning models."""
    def __init__(self, covariates: ee.Image, points: ee.FeatureCollection, targetProperty: str, nFolds: int, proj: str = 'EPSG:4326'):
        """
        Args:
            covariates (ee.Image): ee.Image
            points (ee.FeatureCollection): ee.FeatureCollection
            targetProperty (str): name of the property that contains the target variable
            nFolds (int): number of folds for cross validation
            proj (str): projection of the data
        """

        self.covariates = covariates
        self.points = points
        self.targetProperty = targetProperty
        self.nFolds = nFolds
        self.proj = proj

    def addCoordProperty(self, features: ee.FeatureCollection) -> ee.FeatureCollection:
        """
        This function adds coordinates to the points

        Args:
            features (ee.FeatureCollection): ee.FeatureCollection

        Returns:
            ee.FeatureCollection: ee.FeatureCollection
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
    
    def covariatesToPoints(self) -> ee.FeatureCollection:
        """
        This function extracts the covariates at the points
        
        Returns:
            ee.FeatureCollection: ee.FeatureCollection"""
        # Extract image values at points
        allData = self.covariates.reduceRegions(collection = self._preparePoints(),
                                       reducer = ee.Reducer.first(),
                                       scale = 10,
                                       tileScale = 8)
        return allData