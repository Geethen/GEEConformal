import ee
from geeml.utils import eeprint

class conformalRegressor(object):
    def __init__(self, inferenceImage: ee.Image, calibration: ee.FeatureCollection, test: ee.FeatureCollection, responseCol:str, alpha: float):
        self.inferenceImage = inferenceImage
        self.propertyNames = inferenceImage.bandNames()
        self.alpha = alpha
        self.calibration = calibration
        self.test = test
        self.responseCol = responseCol

    # Calibration stage
    def _computeScores(self):
        """ Compute nonconformity scores based absolute residuals (|y-yhat|)

        Args:
            calibration (ee.FeatureCollection): contains probability of each class and reference label
            alpha (float): Where 0<alpha<1. a alpha of 0.1, implies a 90% coverage. Default = 0.1
            responseCol (str): The name of the property that contains the reference label

        Returns:
            (ee.Feature): ee.Feature that contains two properties qLevel and qHat
            
        """ 
        # Compute nonconformity scores (|y-yhat|)
        def nonConformityScores(feature):
            return feature.set('score', (feature.getNumber(self.label).subtract(feature.getNumber(self.inferenceImage.bandNames())).abs()))
        # Compute quantile level (qLevel) after finite sample correction
        def qLevel():
            return ee.Number(1).subtract(ee.Number(self.alpha))
        # Compute qLevel for nonconformity scores (qHat)
        def qHat(scores):
            return ee.Number(scores.reduce(ee.Reducer.percentile([self.qLevel.multiply(100)])))
        
        scores = self.calibration.map(lambda ft: nonConformityScores(ft)).aggregate_array('score')
        self.qLevel = ee.Number(qLevel())
        self.qHat = ee.Number(qHat(scores))

        return ee.Feature(None, {'qLevel': self.qLevel, 'qHat': self.qHat})

    # Inference stage
    def quantifyImageUncertainty(self):
        """
        Quantify uncertainty for specified alpha using calibrated conformalPredictor

        Args:
            probImage (ee.Number): Quantile level (qLevel) for which to compute uncertainty

        Returns:
            (ee.Image): A band for binary mask for each class (0: excluded from set, 1: inluded in set)
                and the length of each pixels' set.
        """
        feature = self._computeScores()
        qHat = ee.Number(feature.get('qHat'))
        qHatImage = ee.Image.constant(qHat)
        classNames = self.probImage.bandNames()
        def setMask(band):
            return ee.Image(self.probImage.select([band]).gte(qHatImage).set('class',band)).toInt().rename('band')
        # Compute binary mask for each class
        # eeprint(classNames.map(setMask))
        setMasks = ee.ImageCollection(classNames.map(lambda band: setMask(band)))
        # Compute the length (number of included classes) for each set
        setLength = ee.ImageCollection(setMasks).sum().rename('setLength')
        return ee.Image(setMasks.toBands()).addBands(setLength)

    # Evaluate conformalPredictor
    def _quantifyTestUncertainty(self):
        """
        Obtain the classification sets for the test data partition

        Args:
            test (ee.FeatureCollection): 

        Returns:
            ee.FeatureCollection: Contains three additional properties, 
                1) classSet - The set for the test feature
                2) cumProb - The sum of all the class set probabilities
                3) refLabel - The actual label for the test point
        """

        # Create a function to iterate over the sorted probabilities.
        def iterateOverProbabilities(feature, previous):

            previous = ee.Feature(previous)
            # Get the class name and probability of the current feature.
            className = feature.get('class_name')
            probability = feature.getNumber('probability')
            
            # Get the probability of the previous feature.
            prevProb = previous.getNumber('probability')

            newSum = ee.Number(ee.Algorithms.If(probability.gte(self.qHat),
                        prevProb.add(probability),
                        prevProb))
            
            classNames = ee.Algorithms.If(probability.gte(self.qHat),
                        ee.List([previous.get('class_name')]).add(className).flatten(),
                        previous.get('class_name'))
  
            return ee.Feature(None, {
                'refLabel': ee.Algorithms.String(feature.get('label')),
                'class_name': classNames,
                'probability': newSum
            })            

        def computeSets(id):
            filteredCollection = featureCollection.filter(ee.Filter.eq('id', id))
            #   cumProb serves as the first feature for iterateProbabilities
            cumProb = ee.Feature(None).set('probability',0).set('class_name',[])
            result = filteredCollection.iterate(iterateOverProbabilities, cumProb)
            return result

        
        # Create a new feature with 4 properties: feature id, label, class and corresponding probability. 
        # For each class probability, generate a feature
        featureCollection = ee.FeatureCollection(self.test.map(lambda ft: ee.FeatureCollection(
            self.propertyNames.map(lambda propertyName: ee.Feature(None,
                                                                    {'id': ft.id(),
                                                                    'label': ft.get(self.label),
                                                                    'class_name': propertyName,
                                                                    'probability': ee.Number(ft.get(ee.Algorithms.String(propertyName)))}))
                                        ))).flatten()
        # Determine the sets for each test feature
        uid = featureCollection.aggregate_array('id').distinct()
        sets = ee.FeatureCollection(uid.map(lambda id: computeSets(id)))
        return sets

    def evaluateUncertainty(self):
        """
        Computes the average set size and the empirical marginal coverage

        Args:
            test (ee.FeatureCollection): 

        Returns:
            ee.Feature: Contains two properties, 
                1) Avereage set size - The average set length across all pixels in the test featureCollection
                2) Empirical marginal coverage- The (marginal) coverage achieved by the conformal predictor based on the test data
        """
        #  Compute average set size
        def computeSetSize(ft):
            return ee.Feature(None, {'setSize':ee.List(ft.get('class_name')).length()})
        
        
        # Compute empirical marginal coverage (based on test set)
        def computeCoverage(ft):
            # searchString = ft.get('refLabel')
            # if refLabel does not map directly to target classes (for example DW), then use below
            searchString = ee.String(self.clsDict.get(ft.get('refLabel')))
            sets =  ee.List(ft.get('class_name'))
            result = ee.Algorithms.If(
              sets.contains(searchString), # Check if the list contains the string
              1, 0)                  # Return 1 if yes, 0 if no
            return ee.Feature(None, {'coverage':result})
        
        nTest = self.test.size()
        sets = self._quantifyTestUncertainty()
        avgSetSize = sets.map(computeSetSize).aggregate_sum('setSize').divide(nTest)

        coverage = sets.map(computeCoverage).aggregate_sum('coverage').divide(nTest)
        print('Average set size:', "{:.2f}".format(avgSetSize.getInfo()))
        print('Empirical (marginal) coverage:', "{:.2f}".format(coverage.getInfo()))
        return ee.Feature(None, {'avgSetSize':avgSetSize, 'empiricalCoverage':coverage})

