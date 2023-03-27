import ee
# This class is used to calculate average accuracy and confusion matrix for a set of folds
# The class takes in an multi-band image of classification results, number of classes and number of folds
# A confusion matrix is calculated by summing up the confusion matrixes from each fold
# The average accuracy is calculated by weighting each fold by the number of samples in each fold
class prepareMetrics:
    """class to calculate average accuracy and confusion matrix for a set of folds"""
    def __init__(self, classImage: ee.Image, nClasses: int, nFolds: int):
        """classImage (ee.Image): multi-band image of classification results. Each band is
          one classification output from a fold.
           nClasses (int): number of classes
           nFolds (int): number of folds"""
        
        self.classImage = classImage
        self.nClasses = nClasses
        self.nFolds = nFolds
        
    def averageAccuracy(self) -> ee.Number:
        """calculate av acc  by  weighting for validation sample size"""
        acc_arr = self.classImage.aggregate_array('acc')
        acc_num = self.classImage.aggregate_array('num')
        self.acc_raw = self.classImage.aggregate_array('raw')
        tot = acc_num.reduce(ee.Reducer.sum())

        # the weight for each sample
        weight = acc_num.map(lambda item: ee.Number(item).divide(tot))
        # final accuracy
        acc_final = ee.Array(weight).multiply(ee.Array(acc_arr)).reduce(ee.Reducer.sum(),[0])
        print(f'The average weighted accuracy is {acc_final.getInfo()} across {self.nFolds} folds')
        return acc_final
    
    def confusionMatrix(self) -> ee.Image:
        """sum confusion matrices for each fold

        returns ee.Image with accuracy and confusion matrices as properties"""
        
        # first create an empty confusion matrix
        first = ee.Array(ee.List.repeat(0, self.nClasses)).repeat(axis=1,copies= self.nClasses)
        first = ee.List([first])
        
        acc_final = self.averageAccuracy()
        
        def accumulate(item, lst):
            """funciton to sum up confusion matrixes"""
            previous = ee.Array(ee.List(lst).get(-1))
            added = ee.Array(item).add(previous)
            return ee.List(lst).add(added)

        # apply function
        con_matrix = ee.List(self.acc_raw.iterate(accumulate, first)).get(self. nFolds)

        # create confusion matrix from results and calc accuracies
        con_matrix = ee.ConfusionMatrix(con_matrix)
        pa = con_matrix.producersAccuracy()
        ca = con_matrix.consumersAccuracy()
        
        # summarize result to single image
        result_final = self.classImage.mode()

        # set properties of summary to accuracy metrics
        result_final = result_final.set(
          'acc', acc_final,
          'confusion', con_matrix,
          'pa', pa,
          'ca', ca)
        
        return result_final