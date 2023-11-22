import ee
from geeml.utils import eeprint

class conformalFeatureClassifier(object):
    def __init__(self, data: ee.FeatureCollection, bands: list, alpha: float, split: float, label: str, version: str):
        self.data = data
        self.bands = bands
        self.alpha = alpha
        self.split = split
        self.label = label
        self.version = version

    # Function 1
    def _computeScores(self, feature):
        """
        Computes nonconformity scores and number of pixels in label image

        Args:
            feature (ee.Feature): 

        Returns:
            ee.Feature with 'score' property containing nonconformity score

        """
        score = ee.Number(feature.getNumber(self._createClassDictionary().getString(ee.Algorithms.String(feature.get(self.label)))))
        return feature.set('score', ee.Number(score))
    
    # Function 2
    def _createClassDictionary(self):
        """ Create dictionary that maps label values to property names (probability of classes)

        Returns:
            clsDict (ee.Dictionary): Contains integer (keys) and corresponding string labels (values)
        """
        # create class index dictionary
        NCLASSES = len(self.bands)-1
        clsIndex = ee.List.sequence(0, NCLASSES).map(lambda value: ee.Algorithms.String(ee.Number(value).int()))
        clsDict = ee.Dictionary.fromLists(clsIndex, ee.List(self.bands))
        return clsDict

    # Function 3
    def _computeQLevel(self, nCal: int):
        """
        Compute adjusted quantile level (qLevel). Adjustment for finite sample.
        Quantile converted to percentile (x 100) for GEE purposes.

        Args:
            nCal (float): The number of calibration samples/features
        
        Returns:
            qLevel (ee.Number): The adjusted 

        """
        qLevel = ee.Number.expression(**{
            'expression': '100-((ceil((nCal+1)*(1-alpha))/nCal)*100)',
            'vars': {
                'nCal': ee.Number(nCal),
                'alpha': ee.Number(self.alpha)
        }})
        return qLevel

    # Function 4
    def _calibration_evaluation_split(self, seed: int = 42):
        """
        Split the data into calibration and test set.
        """
        # split the calibration data into training and validation sets
        # create a random column
        self.data = self.data.randomColumn(seed = seed)
        # split data
        self.calibration = self.data.filter(ee.Filter.lt('random', self.split))
        self.test = self.data.filter(ee.Filter.gte('random', self.split))

    # Combine function for calibration
    def calibrate(self):
        """
        Calibrates the conformal classifier model
        """
        # Get calibration data
        self._calibration_evaluation_split()
        Cal = self.calibration

        # Compute nonconformaity scores
        scores = ee.FeatureCollection(Cal.map(lambda ft: self._computeScores(ft)))

        # Compute adjusted quantile level
        qLevel = self._computeQLevel(Cal.size())

        # Compute qHat threshold based on qLevel
        qHat = scores.reduceColumns(**{
        'reducer':ee.Reducer.percentile([qLevel]), 
        'selectors': ['score']
            }).values().get(0)
        
        self.qhat = qHat
                
        return ee.Feature(None, {'version': self.version,'qLevel': qLevel, 'qHat': self.qhat})

    # Function 1
    def _computeSets(self):
        """
        Compute the sets for a given feature
        """

    # Create a function to iterate over the sorted probabilities.
        def iterateOverProbabilities(feature, previous):

            previous = ee.Feature(previous)
            # Get the class name and probability of the current feature.
            className = feature.getString('class_name')
            probability = feature.getNumber('probability')
            
            # Get the probability of the previous feature.
            prevProb = previous.getNumber('probability')

            newSum = ee.Number(ee.Algorithms.If(probability.gte(self.qhat),
                        prevProb.add(probability),
                        prevProb))
            
            classNames = ee.Algorithms.If(probability.gte(self.qhat),
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
            ee.List(self.bands).map(lambda propertyName: ee.Feature(None,
                                                                    {'id': ft.id(),
                                                                    'label': ft.get(self.label),
                                                                    'class_name': propertyName,
                                                                    'probability': ee.Number(ft.get(ee.Algorithms.String(propertyName)))}))
                                        ))).flatten()
        # Determine the sets for each test feature
        uid = featureCollection.aggregate_array('id').distinct()
        sets = ee.FeatureCollection(uid.map(lambda id: computeSets(id)))
        return sets
       
    # Function 2
    def _computeSetLength(self, ft):
        """
        Compute average set size
        """
        return ee.Feature(None, {'setSize': ee.List(ft.get('class_name')).length()})
    
    # Function 3
    def _computeCoverage(self, ft):
        """
        Compute coverage (based on test set)
        """
        clsDict = self._createClassDictionary()
        searchString = ee.String(clsDict.getString(clsDict.keys().getNumber(ft.get('refLabel'))))
        sets =  ee.List(ft.get('class_name'))
        result = ee.Algorithms.If(
          sets.contains(searchString), # Check if the list contains the string
          1,                       # If yes, return 1
          0                        # If no, return 0
        )
        return ee.Feature(None,{'CorrectSets':result})

    # Combine functions for evaluation of conformal predictor
    def evaluate(self):
        """
        Evaluates the conformal classifier model
        """
        # Get test data - Used to evaluate conformal classifier
        nTest = self.test.size()

        Sets = self._computeSets()
        
        # Compute average set size(sum of set lengths/ number of test label pixels)
        avgSetSize = Sets.map(lambda ft: self._computeSetLength(ft)).aggregate_sum('setSize').divide(nTest)

        # Evaluate Marginal coverage (based on test set): compute coverage (correct sets/total label pixels/)
        coverage = Sets.map(lambda ft: self._computeCoverage(ft)).aggregate_sum('CorrectSets').divide(nTest)
        eeprint(coverage)

        print('Average set size:', "{:.2f}".format(avgSetSize.getInfo()))
        print('Empirical (marginal) coverage:', "{:.2f}".format(coverage.getInfo()))
              
        return ee.Feature(None, {'version': self.version, 'Empirical Marginal Coverage': coverage, 'Average Prediction Set Size': avgSetSize})

    def predict(self):
        """
        Predicts the conformal classifier model
        """
        pass
        


class conformalImageClassifier(object):
    def __init__(self, probImage: ee.Image, calibration: ee.FeatureCollection, test: ee.FeatureCollection, label:str, alpha: float):
        self.probImage = probImage
        self.propertyNames = probImage.bandNames()
        self.alpha = alpha
        self.calibration = calibration
        self.test = test
        self.label = label

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

