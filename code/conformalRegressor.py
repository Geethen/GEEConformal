import ee
from typing import Union
from geeml.utils import eeprint

# steps
# Calibration
    # compute nonconformity scores
    # compute qHat using qLevel
# Evaluation
    # check average prediction width
    # Check empirical marginal
# Inference
    # make predictions
    # add and subtract qhat to get upper and lower bound. 
    # compute length

class conformalFeatureRegressor(object):
    """
    A class for calibrating and evaluating a conformal predictor to perform inference for a regression task.
    An input FeatureCollection with properties of the reference (label) and predicted values (bands).
    The output can be in the form of a FeatureCollection or an ImageCollection. Currently the only method supported
    is based on the absolute residuals.
    """
    def __init__(self, data: ee.FeatureCollection, bands: list, alpha: float, label: str, version: str):
        """
        Args:
            data (ee.FeatureCollection): A FeatureCollection that contains two compulsory properties;
              1) a reference value and a 2) predcited value.
            bands (str): A feature-level property name corresponding to the predicted values
            alpha (float): The tolerance level between 0-1 denoting the amount of allowable errors.
              For example, a value of 0.1 corresponds to 10% allowable errors and conversely a (1-alpha) 90% confidence level.
            label (str): A feature-level property name corresponding to the reference/expected value.
            version (str): A user-provided string to indicate details of the experiment or date of the experiment.
              By default a datetime stamp is provided in the format (ddmmyyyyssmmhh)
        """
        self.data = data
        self.bands = bands
        self.alpha = alpha
        self.label = label
        self.version = version
    
    # Calibration stage
    # Function 1
    def _calibration_evaluation_split(self, split: float, seed: int = 42):
        """
        Split the data into a calibration and test set.
        """

        # split the calibration data into training and validation sets
        # add a random column with a uniform distribution
        self.data = self.data.randomColumn(seed = seed)
        # split data into calibration and test data
        self.calibration = self.data.filter(ee.Filter.lt('random', split))
        self.test = self.data.filter(ee.Filter.gte('random', split))

    # Function 2
    def calibrate(self, split: float, seed: int = 42):
        """ Calibrate a conformal regressor on the calibration set based on absolute residual (|y-yhat|)nonconformity scores.

        Args:
            split (float): The proportion of the data used to calibrate a conformal regressor. The remainder is used for
             evaluating the conformal predictor.
            seed (int): The seed used to split the data

        Returns:
            (ee.Feature): ee.Feature that contains two properties qLevel and qHat. Here, qLevel corresponds to
              the quantile to be computed. For example, a alpha value of 0.1 corresponds to a quantile level of
              0.9. qHat represents a threshold of the target variable to be estimated.
            
        """ 
        self.split = split
        self.seed = seed
        # Compute nonconformity scores (|y-yhat|)
        def nonConformityScores(feature):
            return feature.set('score', (feature.getNumber(self.bands).subtract(feature.getNumber(self.label)).abs()))
        # Compute quantile level (qLevel) after finite sample correction
        def qLevel():
            self.qlevel = ee.Number(1).subtract(ee.Number(self.alpha))
            return self.qlevel
        # Compute qLevel for nonconformity scores (qHat)
        def qHat(scores):
            qLevel()
            return ee.Number(scores.reduce(ee.Reducer.percentile([self.qLevel.multiply(100)])))
        
        # Split data
        self._calibration_evaluation_split(split = self.split, seed = self.seed)
        # Compute nonconformity scores and convert to array
        scores = self.calibration.map(lambda ft: nonConformityScores(ft)).aggregate_array('score')
        
        # Compute qhat
        self.qhat = ee.Number(qHat(scores))

        return ee.Feature(None, {'qLevel': self.qLevel, 'qHat': self.qhat})
    
    # Inference Stage
    # Function 1
    def predict(self, input: Union(ee.Image, ee.Feature)):
        """
        Quantify uncertainty for a ee.Feature or ee.Image.

        Args:
            input (ee.Image or ee.Feature): If an ee.Image input is provided then a single band image should be provided
             containing the predictions from a regressor. If a ee.Feature is provided, then a property name matching that
             of the 'band' argument should be provided.
        
        Returns:
            An ee.Image or ee.Feature (corresponds to the input type) with three additional bands/properties, specifically,
            1) lower, 2) upper and 3) width. lower corresponds to the lower bound of the prediction interval. upper corresponds
            to the upper bound of the prediction interval. While width corresponds to the difference between the upper and lower
            bound (upper - lower) and represents the prediction width. Owing to the absolute residual method used, all widths
            should be the same.
             
        """
        # Check input type
        if input.name().getInfo() == 'ee.Image':
            # Create a constant image for qhat
            qHatImage = ee.Image.constant(self.qHat)
            # Compute the lower, upper bound of the prediction interval and the width between the two
            lower = ee.Image(input).subtract(qHatImage).rename('lower')
            upper = ee.Image(input).add(qHatImage).rename('upper')
            width = upper.subtract(lower).rename('width')
            # Add output bands to final output
            output = input.addBands([lower, upper, width]) 
        elif input.name().getInfo() == 'ee.Feature':
            # Compute the lower, upper bound of the prediction interval and the width between the two
            lower  = ee.Feature(input).getNumber(self.band).subtract(self.qhat).rename('lower')
            upper = ee.Feature(input).getNumber(self.band).add(self.qhat).rename('upper')
            width = upper.subtract(lower).rename('width')
            # Add output properties to the input feature
            output = ee.Feature(input).set({'lower': lower, 'upper': upper, 'width': width})
        return output

    
    # Evaluation stage
    # Function 1
    def _checkInclusion(self, feature):
        """
        Checks if the predicted value falls within the upper and lower bounds of the prediction interval

        Args: 
            feature (ee.Feature): A feature with a prediction, lower and upper bound.
            
        Returns:
            A null feature (no geometry) with a property called 'CorrectSets' and a value of 1, if the predicted
             value falls within the prediction interval and a zero if not.

        """
        prediction = feature.get(self.band)
        lower = feature.get('lower')
        upper = feature.get('upper')
        result = ee.Algorithms.If(prediction.gte(lower).And(prediction.lte(upper)), # Check if the list contains the string
          1,                       # If yes, return 1
          0                        # If no, return 0
        )
        return ee.Feature(None,{'CorrectSets':result})
    
    # Function 2
    def evaluate(self):
        """
        Evaluates the conformal classifier model

        Returns:
            An ee.Feature with three properties, the empirical marginal coverage, Average prediction
             interval width and the version information.

        """
        # Compute lower and upper bounds of interval
        Intervals = self.test.map(lambda input: self.predict(input))
        
        # Compute average set size(sum of set lengths/ number of test label pixels)
        avgSetSize = Intervals.aggregate_mean('width')

        # Evaluate Marginal coverage (based on test set): compute coverage (correct sets/total label pixels/)
        coverage = Intervals.map(lambda ft: self._checkInclusion(ft)).aggregate_sum('CorrectSets').divide(self.test.size())

        print('Average prediction width:', "{:.2f}".format(avgSetSize.getInfo()))
        print('Empirical (marginal) coverage:', "{:.2f}".format(coverage.getInfo()))
              
        return ee.Feature(None, {'version': self.version, 'Empirical Marginal Coverage': coverage, 'Average Prediction Width': avgSetSize})
    
class conformalImageRegressor(object):
    """
    A class for calibrating and evaluating a conformal predictor to perform inference for a regression task.
    An input ImageCollection with a band containing the reference (label) and predicted values (bands).
    The output can be in the form of a FeatureCollection or an ImageCollection. Currently the only method supported
    is based on the absolute residuals.
    """
    def __init__(self, data: ee.FeatureCollection, bands: list, alpha: float, label: str, version: str):
        """
        Args:
            data (ee.FeatureCollection): An ImageCollection that contains two compulsory bands;
              1) a reference value and a 2) predcited value.
            bands (str): A image-level property name corresponding to the predicted values
            alpha (float): The tolerance level between 0-1 denoting the amount of allowable errors.
              For example, a value of 0.1 corresponds to 10% allowable errors and conversely a (1-alpha) 90% confidence level.
            label (str): A image-level property name corresponding to the reference/expected value.
            version (str): A user-provided string to indicate details of the experiment or date of the experiment.
              By default a datetime stamp is provided in the format (ddmmyyyyssmmhh)
        """
        self.data = data
        self.bands = bands
        self.alpha = alpha
        self.label = label
        self.version = version
    
    # Calibration stage
    # Function 1
    def _calibration_evaluation_split(self, split: float, seed: int = 42):
        """
        Split the data into a calibration and test set.
        """

        # split the calibration data into training and validation sets
        # add a random column with a uniform distribution
        self.data = self.data.randomColumn(seed = seed)
        # split data into calibration and test data
        self.calibration = self.data.filter(ee.Filter.lt('random', split))
        self.test = self.data.filter(ee.Filter.gte('random', split))

    # Function 2
    def calibrate(self, image, split: float, scale: int, seed: int = 42):
        """ Calibrate a conformal regressor on the calibration set based on absolute residual (|y-yhat|) nonconformity scores.

        Args:
            split (float): The proportion of the data used to calibrate a conformal regressor. The remainder is used for
             evaluating the conformal predictor.
            scale (int): The scale used to apply the reduce functions. Ideally should match native resolution of data or
             coarser if memory limts are reached
            seed (int): The seed used to split the data

        Returns:
            (ee.Feature): ee.Feature that contains two properties qLevel and qHat. Here, qLevel corresponds to
              the quantile to be computed. For example, a alpha value of 0.1 corresponds to a quantile level of
              0.9. qHat represents a threshold of the target variable to be estimated.
            
        """ 
        self.split = split
        self.scale = scale
        self.seed = seed
        
        # Compute nonconformity scores (|y-yhat|)
        def nonConformityScores(image):
            return image.select(self.bands).subtract(image.select(self.label)).abs().rename('score')
        # Compute quantile level (qLevel) (1-alpha). multiply quantile by 100 to compute percentile 
        # (quantile not supported in GEE)
        def computeQLevel():
            self.qlevel = ee.Number(1).subtract(ee.Number(self.alpha)).multiply(100)
        # Compute  qHat threshold based on qLevel per image
        def computeQHat(image):
            computeQLevel()
            qHat = ee.Image(image).reduceRegion(**{'reducer':ee.Reducer.percentile([self.qlevel]),
                                                'geometry': image.geometry(),
                                                'scale': self.scale,
                                                'tileScale': 16,
                                                'maxPixels': 1e9}).get('score')
            return image.set('qHat', qHat)
        
        # Compute aggregate qHat threshold based on qLevel
        scores = self.test.map(lambda image: nonConformityScores(image))
        self.qhat = scores.map(lambda img: computeQHat(img)).reduceColumns(**{
        'reducer':ee.Reducer.percentile([self.qlevel]), 
        'selectors': ['qHat']
            }).values().get(0)
                
        return ee.Feature(None, {'version': self.version,'qLevel': self.qlevel, 'qHat': self.qhat})
    
    # Inference Stage
    # Function 1
    def predict(self, input: Union(ee.Image, ee.Feature)):
        """
        Quantify uncertainty for a ee.Feature or ee.Image.

        Args:
            input (ee.Image or ee.Feature): If an ee.Image input is provided then a dual band image should be provided
             containing the predictions from a regressor and the reference/expected values. If a ee.Feature is provided,
             then a property name matching that of the 'band' argument should be provided.
        
        Returns:
            An ee.Image or ee.Feature (corresponds to the input type) with three additional bands/properties, specifically,
            1) lower, 2) upper and 3) width. lower corresponds to the lower bound of the prediction interval. upper corresponds
            to the upper bound of the prediction interval. While width corresponds to the difference between the upper and lower
            bound (upper - lower) and represents the prediction width. Owing to the absolute residual method used, all widths
            should be the same.
             
        """
        # Check input type
        if input.name().getInfo() == 'ee.Image':
            # Create a constant image for qhat
            qHatImage = ee.Image.constant(self.qHat)
            prediction = input.select(self.band)
            # Compute the lower, upper bound of the prediction interval and the width between the two
            lower = prediction.subtract(qHatImage).rename('lower')
            upper = prediction.add(qHatImage).rename('upper')
            width = upper.subtract(lower).rename('width')
            # Add output bands to final output
            output = input.addBands([lower, upper, width]) 
        elif input.name().getInfo() == 'ee.Feature':
            # Compute the lower, upper bound of the prediction interval and the width between the two
            lower  = ee.Feature(input).getNumber(self.band).subtract(self.qhat).rename('lower')
            upper = ee.Feature(input).getNumber(self.band).add(self.qhat).rename('upper')
            width = upper.subtract(lower).rename('width')
            # Add output properties to the input feature
            output = ee.Feature(input).set({'lower': lower, 'upper': upper, 'width': width})
        return output

    
    # Evaluation stage
    # Function 1
    def _checkInclusion(self, image):
        """
        Checks if the predicted value falls within the upper and lower bounds of the prediction interval

        Args: 
            image (ee.Image): A multi-band image with the reference/expected value band and a prediction,
             lower and upper bound band.
            
        Returns:
            A binary image is returned with a band called 'CorrectSets'. Where, a value of 1, if the predicted
             value falls within the prediction interval and a zero if not. A 'sumPixels' property is added and
             corresponds to the total number of pixels that contain the expected value within their prediction
             interval. Additionally, a 'nPixels' property is added and corresponds to the number of pixels there
             in the reference band.

        """
        prediction = image.select(self.band)
        label = image.select(self.label)
        lower = image.select('lower')
        upper = image.selct('upper')
        width = image.select('width')
        # Check if the list contains the prediction within the prediction interval. If yes, return 1. If no, return 0.
        result = prediction.gte(lower).And(prediction.lte(upper)).rename('CorrectSets')
        # Sum the lengths of all sets in set length image- used to compute average set size and the width.
        sumPixels = result.addBands(width).reduceRegion(**{'reducer':ee.Reducer.sum(),
                                              'geometry': image.geometry(),
                                              'scale': self.scale,
                                              'tileScale': 16,
                                              'maxPixels': 1e9})
        # Compute the number of pixels in test label image
        nPixels = label.reduceRegion(**{'reducer':ee.Reducer.count(),
                                             'geometry': image.geometry(),
                                             'scale': self.scale,
                                             'tileScale': 16,
                                             'maxPixels': 1e9}).getNumber(self.label)
        return result.set('sumPixels', sumPixels.getNumber('CorrectSets')).set('nPixels', nPixels)\
            .set('width', sumPixels.getNumber('width')).copyProperties(image)
    
    # Function 2
    def evaluate(self):
        """
        Evaluates the conformal classifier model

        Returns:
            An ee.Feature with three properties, the empirical marginal coverage, Average prediction
             interval width and the version information.

        """
        # Compute lower and upper bounds of interval
        Intervals = self.test.map(lambda input: self._checkInclusion(self.predict(input)))

        # Compute the number of pixels in label test set
        nPixelsTest = Intervals.aggregate_sum('nPixels')
        
        # Compute average set size(sum of set lengths/ number of test label pixels)
        avgSetSize = Intervals.aggregate_sum('width').divide(nPixelsTest)

        # Evaluate Marginal coverage (based on test set): compute coverage (correct sets/total label pixels/)
        coverage = Intervals.aggregate_sum('sumPixels').divide(nPixelsTest)

        print('Average width of prediction interval:', "{:.2f}".format(avgSetSize.getInfo()))
        print('Empirical (marginal) coverage:', "{:.2f}".format(coverage.getInfo()))
              
        return ee.Feature(None, {'version': self.version, 'Empirical Marginal Coverage': coverage, 'Average Prediction Width': avgSetSize})