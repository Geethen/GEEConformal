import os
from typing import Union
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.plot import reshape_as_image
import ee
from sklearn.ensemble import RandomForestClassifier

from geemap import ee_to_df

# from mapie.calibration import MapieCalibrator
# from mapie.metrics import top_label_ece

from geedim.download import BaseImage
from geeml.utils import eeprint

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

    def _UQ(self, fold:int) -> Union[ee.FeatureCollection, ee.FeatureCollection, ee.FeatureCollection]:
        """function to apply data splitting appropriate when conformal prediction is used.

        Returns:
            training, validation and calibration dataset (ee.FeatureCollections)"""
        
        def train_test_split(split: float)-> Union[ee.FeatureCollection, ee.FeatureCollection]:
            """Function to split a dataset into two portions based on train portion (split). Results in 
               a near stratified sample. There is statistical error associated with random.
            
            Args
                split (float): train proportion. Will not return exact number of samples
                
            Returns
                train (ee.FeatureCollection), test (ee.FeatureCollection) """
            
            ## define fraction for training (remainder is for testing)
            data = self.dataset.randomColumn(seed=42)
            ## divide into training and testing sets based on the split
            training = data.filter(ee.Filter.lt('random', split))
            validation = data.filter(ee.Filter.gte('random', split))
            return training, validation
        
        remainder, calibration = train_test_split(split = 0.9)

        # Choose a fold (self.seed is equal to the fold)
        training = remainder.filter(ee.Filter.neq("cluster", fold))
        validation = remainder.filter(ee.Filter.eq("cluster", fold))
        return training, validation, calibration
    
    @property
    def calibrationData(self) -> pd.DataFrame:
        """function to get calibration data as a pandas dataframe

        Returns:
            ee.FeatureCollection: calibration data"""
        #selected fold is irrelevant here. fold is only used to create train + val datasets
        _, _, calibration = self._UQ(fold = 1)
        cal = ee_to_df(calibration)
        X_cal, y_cal = cal[self.bandNames.getInfo()].values, cal[[self.responseCol]].values.squeeze()
        return X_cal, y_cal
    
    @property
    def fittedClassifier(self) -> RandomForestClassifier:
        """function to fit a random forest model on the combined train and validation data
        
        Returns:
            scikit learn RandomForest classifer: classified image with accuracy and confusion matrix as properties"""

        training, validation, _ = self._UQ(fold = 1)
        train = ee_to_df(training)
        val = ee_to_df(validation)
        df = pd.concat([train, val])
        #train and apply classifier
        classifier = RandomForestClassifier(n_estimators=50, max_depth=None, min_samples_split=2,
                                             min_samples_leaf=1, max_features=20, bootstrap=True,
                                             oob_score=False, n_jobs=-1, random_state=0, verbose=0,
                                             warm_start=False, class_weight=None)
        classifier.fit(df[self.bandNames.getInfo()], df[[self.responseCol]])
        return classifier
    
    # @property
    # def calibratedClassifier(self):

    #     X_cal, y_cal = self.calibrationData
    #     clf = self.fittedClassifier

    #     mapie_reg = MapieCalibrator(estimator=clf, cv="prefit", calibrator="isotonic")
    #     mapie_reg.fit(X_cal, y_cal)
    #     return mapie_reg
    
    def inference(self, mode : str, infile: str, model, confModel, outfile : str, patchSize : int, num_workers : int = 4):
        """
        Run inference on infile (Geotiff) using trained model.

        Args:
            mode (str): one of 'sets', 'predict', 'predict_proba' or all. Defaults to 'all'
            infile (str):
            model: a model with a predict and predict_proba method
            confModel (mapie classifier): Calibrated conformal predictor based on the MAPIE package.
            outfile (str): File path and file name to save output geoTiff files
            patchSize (int): The height and width dimensions of the patch to process
            num_workers (int): The number of core to utilise during parralel processing

        Returns:
            multiband (n_classes +2) geotiff in 'all' mode.
            1) A multiband (number of bands equal to the n classes) geotiff ('set'),
            2) A single band geotiff for highest probability (argmax) class ('predict'),
            3) A single band geotiff for the probability of the argmax class ('predict_proba')

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
                        data = pd.DataFrame(new_arr, columns = bandnames).fillna(0)
                        if mode == 'sets':
                            _, y_ps_score = confModel.predict(data, alpha = 0.1)
                            result = y_ps_score.reshape([i_arr.shape[0],i_arr.shape[1], model.n_classes_]).astype(np.float64)
                            nbands = model.n_classes_
                        elif mode == 'predict':
                            result = model.predict(data)
                            # # Reshape our classification map back into a 2D matrix so we can save it as an image
                            result = result.reshape(i_arr[:, :, 0].shape).astype(np.float64)
                            nbands = 1
                        elif mode == 'predict_proba':
                            result = model.predict_proba(data)
                            result = result[~np.isnan(result)]
                            # # Reshape our classification map back into a 2D matrix so we can save it as an image
                            result = result.reshape(i_arr[:, :, 0].shape).astype(np.float64)
                            nbands = 1
                        elif mode == 'all':
                            y_pred_score, y_ps_score = confModel.predict(data, alpha = 0.1)
                            #  predict
                            pred = y_pred_score.reshape(i_arr[:, :, 1].shape).astype(np.float64)
                            print('preds', pred.shape)
                            #  sets
                            sets = y_ps_score.reshape([i_arr.shape[0],i_arr.shape[1], model.n_classes_]).astype(np.float64)
                            print('sets',sets.shape) 
                            # predict_proba
                            result = model.predict_proba(data)
                            result = result[~np.isnan(result)]
                            probs = result.reshape(i_arr[:, :, 1].shape).astype(np.float64)
                            print('probs',probs.shape)
                            # Combine results along the third axis as bands
                            result = np.dstack([pred[:,:, np.newaxis], probs[:,:, np.newaxis], sets])
                            nbands = model.n_classes_+2

                    with write_lock:
                        dst.write(result, nbands, window=window)

                # We map the process() function over the list of windows.
                with tqdm(total=len(windows), desc = os.path.basename(outfile)) as pbar:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                        futures = {executor.submit(process, window): window for window in windows}
                        try:
                            for future in concurrent.futures.as_completed(futures):
                                future.result()
                                pbar.update(1)

                        except Exception as ex:
                            logger.info('Cancelling...')
                            executor.shutdown(wait=False, cancel_futures=True)
                            raise ex

    def _kFoldCV(self, fold: int, uq: bool = False):
        """function to run k-fold cross validation

        Args: 
            fold (int): fold number
        
        Returns:
            ee.Image: classified image with accuracy and confusion matrix as properties"""
        
        #number of classes:
        classorder = self.dataset.aggregate_histogram(self.responseCol).keys().map(lambda number: ee.Number.parse(number))

        if uq:
            training, validation, _ = self._UQ(fold = fold)
        else:
            #choose a fold
            training = self.dataset.filter(ee.Filter.neq("cluster", fold))
            validation = self.dataset.filter(ee.Filter.eq("cluster", fold))

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
    
    def kFoldCV(self, nFolds: int, uq: bool = False) -> ee.ImageCollection:
        result = ee.ImageCollection(ee.List.sequence(0,nFolds-1).map(lambda fold: self._kFoldCV(fold, uq = uq)))
        return result
