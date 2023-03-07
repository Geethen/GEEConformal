import ee
from typing import Union
from geemap import ee_to_pandas
from sklearn.ensemble import RandomForestClassifier
from mapie import MapieClassifier
import pandas as pd
import rasterio

from pathlib import Path
from rasterio.plot import reshape_as_raster, reshape_as_image
import numpy as np

# Parralel processing
import concurrent.futures
import threading
import logging
from tqdm.auto import tqdm

class prepareModel:
    """class to prepare data for model fitting"""
    def __init__(self, dataset: ee.ImageCollection, responseCol: str, inferenceImage: ee.Image, bandNames: list):
        """dataset (ee.ImageCollection): training data
           responseCol (str): name of the response variable
           inferenceImage (ee.Image): image to be classified
           bandNames (list): list of band names"""
        self.dataset = dataset
        self.responseCol = responseCol
        self.inferenceImage = inferenceImage
        self.bandNames = bandNames

    def _UQ(self) -> Union[ee.FeatureCollection, ee.FeatureCollection, ee.FeatureCollection]:
        """function to apply data splitting appropriate when conformal prediction is used.

        Returns:
            training, validation and calibration dataset (ee.FeatureCollections)"""
        
        # take a stratified random sample of 10% of the data
        nClusters = self.dataset.aggregate_array('cluster').distinct()

        def nPoints(cluster, proportion):
            """function to compute the number of points to be taken from each cluster"""
            return self.dataset.filter(ee.Filter.eq('cluster', cluster)).size().multiply(proportion).round()
        
        # for each cluster get npoints.
        calibration = nClusters.map(lambda cluster: ee.List(self.dataset.filter(ee.Filter.eq('cluster', cluster)))\
                                    .slice(0, nPoints(cluster, 0.1))).flatten()
        remainder = nClusters.map(lambda cluster: ee.List(self.dataset.filter(ee.Filter.eq('cluster', cluster)))\
                                    .slice(nPoints(cluster, 0.1), nPoints(cluster, 1)).add(1)).flatten()
        #choose a fold
        training = remainder.filter(ee.Filter.neq("cluster", self.seed))
        validation = remainder.filter(ee.Filter.eq("cluster", self.seed))
        return training, validation, calibration
    
    @property
    def calibrationData(self) -> ee.FeatureCollection:
        """function to get calibration data as a pandas dataframe

        Returns:
            ee.FeatureCollection: calibration data"""
        _, _, calibration = self._UQ()
        cal = ee_to_pandas(calibration)
        return cal
    
    @property
    def fittedClassifier(self) -> ee.Image:
        """function to fit a random forest model on the combined train and validation data
        
        Returns:
            scikit learn RandomForest classifer: classified image with accuracy and confusion matrix as properties"""

        training, validation, _ = self._UQ()
        train = ee_to_pandas(training)
        val = ee_to_pandas(validation)
        df = pd.concat([train, val])
        #train and apply classifier
        classifier = RandomForestClassifier(n_estimators=50, max_depth=None, min_samples_split=2,
                                             min_samples_leaf=1, max_features=20, bootstrap=True,
                                             oob_score=False, n_jobs=-1, random_state=0, verbose=0,
                                             warm_start=False, class_weight=None)
        classifier.fit(df[self.bandNames], df[[self.responseCol]])
        return classifier
    
    @property
    def conformalPredictor(self) -> ee.Image:

        cal = self.calibrationData
        X_cal, y_cal = cal[self.bandNames].values, cal[[self.responseCol]].values.squeeze()
        clf = self.fittedClassifier
        # Initialize the Conformal Prediction classifier
        confPredictor = MapieClassifier(estimator=clf, cv="prefit", method="raps")
        confPredictor.fit(X_cal, y_cal)
        return confPredictor
    
    def inference(self, infile, model, outfile, patchSize, num_workers=4):
        """
        Run inference on infile (Geotiff) using trained model.

        """

        with rasterio.open(infile) as src:
            
            logger = logging.getLogger(__name__)

            # Create a destination dataset based on source params. The
            # destination will be tiled, and the tiles will be processed
            # concurrently.
            profile = src.profile
            profile.update(blockxsize= patchSize, blockysize= patchSize, tiled=True, count=1)

            with rasterio.open(Path(outfile), "w", **profile) as dst:
                windows = [window for ij, window in dst.block_windows()]

                # use a lock to protect the DatasetReader/Writer
                read_lock = threading.Lock()
                write_lock = threading.Lock()

                def process(window):
                    with read_lock:
                        src_array = src.read(window=window)
                        i_arr = reshape_as_image(src_array)

                        #Format input_image for inference
                        nPixels = i_arr.shape[0]*i_arr.shape[1]
                        nBands = i_arr.shape[-1]
                        # Take full image and reshape into long 2d array (nrow * ncol, nband) for classification
                        new_arr = i_arr.reshape(nPixels, nBands)#reshape 3d array to 2d array that matches the training data table from earlier
                        bandnames = list(src.descriptions)
                        result_ = model.predict(pd.DataFrame(new_arr, columns = bandnames).fillna(0))
                        # # Reshape our classification map back into a 2D matrix so we can save it as an image
                        result = result_.reshape(i_arr[:, :, 0].shape).astype(np.float64)

                    with write_lock:
                        dst.write(result, 1, window=window)
                        # bar.update(1)

                # We map the process() function over the list of
                # windows.
                with tqdm(total=len(windows), desc = os.path.basename(outfile)) as pbar:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                        # executor.map(process, windows)
                        futures = {executor.submit(process, window): window for window in windows}
                        try:
                            for future in concurrent.futures.as_completed(futures):
                                future.result()
                                pbar.update(1)

                        except Exception as ex:
                            logger.info('Cancelling...')
                            executor.shutdown(wait=False, cancel_futures=True)
                            raise ex
    
    def localInference(self, mode:str, outFile: str, proj: str = 'EPSG:4326') -> ee.Image:
        """function to make local inference on an image

        Args:
            image (ee.Image): image to be classified
            classifier (ee.Classifier): trained classifier or conformal predictor

        Returns:
            ee.Image: classified image"""
        
        # Download the image- uses geedim
        BaseImage(self.inferenceImage).download(outFile, crs= proj, region = aoi.geometry(),
                                                 scale = 1000, overwrite=True, num_threads=20)
        
        if mode == 'UQ':
            classifier = self.conformalPredictor
        elif mode == 'RF':
            classifier = self.fittedClassifier
        
        # Run inference
        self.inference(model = classifier, infile = outFile, outfile = outFile, patchSize = 128, num_workers=10)

    def _kFoldCV(self, fold: int, uq: bool = False):
        """function to run k-fold cross validation

        Args: 
            fold (int): fold number
        
        Returns:
            ee.Image: classified image with accuracy and confusion matrix as properties"""
        
        self.seed = fold
        
        #number of classes:
        classorder = self.dataset.aggregate_histogram(self.responseCol).keys().map(lambda number: ee.Number.parse(number))

        if uq:
            training, validation, calibration = self._UQ()
        else:
            #choose a fold
            training = self.dataset.filter(ee.Filter.neq("cluster", self.seed))
            validation = self.dataset.filter(ee.Filter.eq("cluster", self.seed))

        #train and apply classifier
        classifier = ee.Classifier.smileRandomForest(**{
            'numberOfTrees':50,
            'maxNodes':None,
            'bagFraction':0.7,
            'minLeafPopulation': 1,
            'variablesPerSplit': 20
        }).train(**{
            'features': training,
            'classProperty':'code',
            'inputProperties': self.bandNames
        })

        #make prediction for entire study area
        classified = self.inferenceImage.classify(classifier)

        #accuracy assessment
        assessment = validation.classify(classifier).errorMatrix(**{
            'actual':self.responseCol,
            'predicted':'classification',
            'order':classorder
        })

        accuracy = assessment.accuracy()
        raw = assessment.array()
        num = validation.size()

        #set accuracy result as a property of classification raster
        classified = classified.set({'acc':accuracy})
        classified = classified.set({'raw':raw})
        classified = classified.set({'num':num})

        return classified
    
    def kFoldCV(self, nFolds: int) -> ee.ImageCollection:
        result = ee.ImageCollection(ee.List.sequence(0,nFolds-1).map(lambda fold: self._kFoldCV(fold)))
        return result
