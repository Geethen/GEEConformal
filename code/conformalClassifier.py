import ee
from geeml.utils import eeprint

# The conformalFeatureClassifier class contains methods to calibrate, evaluate and perform inference for a feature collection
class conformalFeatureClassifier(object):
    def __init__(self, data: ee.FeatureCollection, bands: list, alpha: float, split: float, label: str, version: str):
        self.data = data
        self.bands = bands
        self.alpha = alpha
        self.split = split
        self.label = label
        self.version = version

    # Calibration
    # Function 1
    def _computeScores(self, feature):
        """
        Computes nonconformity scores and number of pixels in label image

        Args:
            feature (ee.Feature): 

        Returns:
            ee.Feature with 'score' property containing nonconformity score

        """
        score = ee.Number(feature.getNumber(self.clsDict.getString(ee.Algorithms.String(feature.get(self.label)))))
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
        self.clsDict = ee.Dictionary.fromLists(clsIndex, ee.List(self.bands))

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

    # Function 5
    # Combine functions for calibration
    def calibrate(self):
        """
        Calibrates the conformal classifier model
        """
        # Get calibration data
        self._calibration_evaluation_split()
        Cal = self.calibration

        # Create class dictionary
        self._createClassDictionary()

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

    # Evaluation
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
        searchString = ee.String(self.clsDict.getString(ft.getString('refLabel')))
        sets =  ee.List(ft.get('class_name'))
        result = ee.Algorithms.If(
          sets.contains(searchString), # Check if the list contains the string
          1,                       # If yes, return 1
          0                        # If no, return 0
        )
        return ee.Feature(None,{'CorrectSets':result})

    # Function 4
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

        print('Average set size:', "{:.2f}".format(avgSetSize.getInfo()))
        print('Empirical (marginal) coverage:', "{:.2f}".format(coverage.getInfo()))
              
        return ee.Feature(None, {'version': self.version, 'Empirical Marginal Coverage': coverage, 'Average Prediction Set Size': avgSetSize})
    
    # Inference
    # Function 1
    # A binary mask is returned for each potential class.
    def predict(self, image):
        """
        Predicts the conformal classifier model
        """
        # create constant image for threshold
        qHatImage = ee.Image.constant(self.qhat)
        # get binary mask, 1(included in set)
        setMasks = ee.ImageCollection(ee.List(self.bands).map(lambda band:
            ee.Image(image).select([band]).gte(qHatImage).set('class',band).rename('band')))
        # get length of set per pixel
        setLength = ee.ImageCollection(setMasks).sum().rename('setLength')
        sets = ee.Image(setMasks.toBands().addBands(setLength)).rename(ee.List(self.bands).add('setLength')).toInt8().updateMask(1)
        return sets
    
    # The conformalImageClassifier class contains methods to calibrate, evaluate and perform inference for a image collection
class conformalImageClassifier(object):
    def __init__(self, data: ee.ImageCollection, scale: int, bands: list, alpha: float, split: float, label: str, version: str):
        self.data = data
        self.scale = scale
        self.bands = bands
        self.alpha = alpha
        self.split = split
        self.label = label
        self.version = version

    # Calibration
    # Function 1
    def _computeScores(self, image):
        """
        A function to compute nonconformity scores and number of pixels in label image

        Args:
            image (ee.Image): 

        Returns:
            ee.Feature with 'score' property containing nonconformity score

        """
        # Select the label band
        labelImage = image.select(self.label).toInt8()
        # Get probs for reference class (used for computing nonconformity score)
        scores = image.select(self.bands).toArray().arrayGet(labelImage)
        # Get the number of pixels in the label image
        nPixels = labelImage.reduceRegion(**{'reducer':ee.Reducer.count(),
                                             'geometry': image.geometry(),
                                             'scale': self.scale,
                                             'tileScale': 16,
                                             'maxPixels': 1e9}).getNumber('label')
        return scores.rename('score').set('nPixels', nPixels)
    
    # Function 2
    def _createClassDictionary(self):
        """ Create dictionary that maps label values to property names (probability of classes)

        Returns:
            clsDict (ee.Dictionary): Contains integer (keys) and corresponding string labels (values)
        """
        # create class index dictionary
        NCLASSES = len(self.bands)-1
        clsIndex = ee.List.sequence(0, NCLASSES).map(lambda value: ee.Algorithms.String(ee.Number(value).int()))
        self.clsDict = ee.Dictionary.fromLists(clsIndex, ee.List(self.bands))

    # Function 3
    def _computeQLevel(self, nCal: int):
        """
        Compute adjusted quantile level (qLevel). Adjustment for finite sample.
        Quantile converted to percentile (x 100) for GEE purposes.

        Args:
            nCal (int): The number of calibration samples/features
        
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
    def _computeQHat(self, image, qLevel):
        """
        Get nonconformaity score that matches with qLevel

        Args:
            image (ee.Image): The image to compute QHat for

        Returns:
            qHat (ee.image): input image with qHat value for the image set as a property
        """
        qHat = ee.Image(image).reduceRegion(**{'reducer':ee.Reducer.percentile([qLevel]),
                                                'geometry': image.geometry(),
                                                'scale': self.scale,
                                                'tileScale': 16,
                                                'maxPixels': 1e9}).get('score')
        return image.set('qHat', qHat)

    # Function 5
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

    # Function 6
    # Combine functions for calibration
    def calibrate(self):
        """
        Calibrates the conformal classifier model
        """
        # Get calibration image data used to calibrate conformal classifier
        self._calibration_evaluation_split()

        # Create class dictionary
        self._createClassDictionary()

        # Compute nonconformaity scores
        scores = ee.FeatureCollection(ee.ImageCollection(self.calibration).map(lambda img: self._computeScores(img)))

        # compute total calibration (label) pixels
        nPixelsCal = scores.aggregate_sum('nPixels')

        # Compute adjusted quantile level
        qLevel = self._computeQLevel(nPixelsCal)

        # Compute qHat threshold based on qLevel
        qHat = scores.map(lambda img: self._computeQHat(img, qLevel)).reduceColumns(**{
        'reducer':ee.Reducer.percentile([qLevel]), 
        'selectors': ['qHat']
            }).values().get(0)
        
        self.qhat = qHat
                
        return ee.Feature(None, {'version': self.version,'qLevel': qLevel, 'qHat': self.qhat})
    
    # Evaluation
    # Function 1
    def _computeSets(self, image: ee.Image):
        """
        A binary mask is returned for each candidate class. 1 represents included in set, 0 represents exclusion.

        Args:
            image (ee.Image): A multiband image with the number of bands equal to the number of candidate classes.
                Each band contains the probability of belonging to a class.
        
        Returns:
            image (ee.Image): A mutiband Image with the number of bands equal to the number of candidate classes.
            The image contains a property called 'sumPixels' that contains the sum of pixels in the image.

        """
        # Create a constant image with qhat at all pixels
        qHatImage = ee.Image.constant(self.qhat)
        # Compute binary mask for each candidate class. 1= included in set, 0 = not included in set
        setMasks = ee.ImageCollection(ee.List(self.bands).map(lambda band: 
                                                     ee.Image(image).select([band])
                                                     .gte(qHatImage).set('class',band).rename('band')))
        # Compute the length of each set/ for each pixel
        setLength = ee.ImageCollection(setMasks).sum().rename('setLength')
        # Format output sets
        sets = ee.Image(setMasks.toBands().addBands(setLength)).rename(ee.List(self.bands).add('setLength')).toInt8().updateMask(1)
        # Sum the lengths of all sets in set length image- used to compute average set size
        sumPixels = setLength.reduceRegion(**{'reducer':ee.Reducer.sum(),
                                              'geometry': image.geometry(),
                                              'scale': self.scale,
                                              'tileScale': 16,
                                              'maxPixels': 1e9}).getNumber('setLength')
        return sets.set('sumPixels', sumPixels)
    
    # Function 2
    def _checkInclusion(self, Sets: ee.ImageCollection, image: ee.Image):
        """
        Compute empirical marginal coverage. If 1, correctly included in set. If 0, incorrectly included in set.
        Uses reference label to select cooresponding band value from the binary set masks.

        Args:
            Sets (ee.ImageCollection): Contains binary masks. 1 values correspond to inclusion into prediction sets,
              0 values correspond to exlusion.
            image (ee.Image): A multiband image with the number of bands equal to the number of candidate classes.
                Each band contains the probability of belonging to a class.
        
        Returns:
            image (ee.Image): A mutiband Image with the number of bands equal to the number of candidate classes.
            The image contains a property called 'sumPixels' that contains the sum of pixels in the image.
        """
        # Filter binary set masks corresponding to test label image, converts to array
        setMasks = ee.Image(Sets.filter(ee.Filter.eq('system:index', image.get('system:index'))).first()).select(self.bands).toInt8().toArray()
        # Select label image (reference labels)
        labelImage = ee.Image(image).select(self.label).toInt8()
        # get binary image. 1= correctly included in set
        inclusion = setMasks.arrayGet(labelImage).rename('coverage')
        # Compute the number of crrect sets (value = 1).
        # Count of 1s divide by totalPixels = coverage
        correctSets = inclusion.selfMask().reduceRegion(**{'reducer':ee.Reducer.count(),
                                                           'geometry': image.geometry(),
                                                            'scale': self.scale,
                                                             'tileScale': 16,
                                                             'maxPixels': 1e9}).getNumber('coverage')
        # Compute the number of pixels in test label image
        nPixels = labelImage.reduceRegion(**{'reducer':ee.Reducer.count(),
                                             'geometry': image.geometry(),
                                             'scale': self.scale,
                                             'tileScale': 16,
                                             'maxPixels': 1e9}).getNumber('label')
        return inclusion.set('correctSets', correctSets).set('nPixels', nPixels).copyProperties(image)
    
    # Function 3
    # Combine functions for evaluation of conformal predictor
    def evaluate(self):
        """
        Evaluates the conformal classifier model
        """
        Sets = ee.ImageCollection(self.test.map(lambda image: self._computeSets(image)))

        # Check reference class inclusion in set
        result = ee.ImageCollection(self.test.map(lambda image: self._checkInclusion(Sets = Sets, image = image)))

        # Compute the number of pixels in label test image
        nPixelsTest = result.aggregate_sum('nPixels')

        # Evaluate Marginal coverage (based on test set): compute coverage (correct sets/total label pixels)
        coverage = result.aggregate_sum('correctSets').divide(nPixelsTest)

        # Compute average set size(sum of set lengths/ number of test label pixels)
        avgSetSize = ee.ImageCollection(Sets).aggregate_sum('sumPixels').divide(nPixelsTest)

        print('Average set size:', "{:.2f}".format(avgSetSize.getInfo()))
        print('Empirical (marginal) coverage:', "{:.2f}".format(coverage.getInfo()))
              
        return ee.Feature(None, {'version': self.version, 'Empirical Marginal Coverage': coverage, 'Average Prediction Set Size': avgSetSize})

    # Inference
    #  Function 1
    #  A binary mask is returned for each candidate class.
    def predict(self, image):
        """
        Predicts the conformal classifier model
        """
        # create constant image for threshold
        qHatImage = ee.Image.constant(self.qhat)
        # get binary mask, 1(included in set)
        setMasks = ee.ImageCollection(ee.List(self.bands).map(lambda band:
            ee.Image(image).select([band]).gte(qHatImage).set('class',band).rename('band')))
        # get length of set per pixel
        setLength = ee.ImageCollection(setMasks).sum().rename('setLength')
        sets = ee.Image(setMasks.toBands().addBands(setLength)).rename(ee.List(self.bands).add('setLength')).toInt8().updateMask(1)
        return sets