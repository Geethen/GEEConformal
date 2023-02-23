import ee
class prepareModel:
    def __init__(self, dataset, responseCol, inferenceImage, bandNames):
        self.dataset = dataset
        self.responseCol = responseCol
        self.inferenceImage = inferenceImage
        self.bandNames = bandNames
        
    def _kFoldCV(self, fold):
        
        self.seed = fold
        
        #number of classes:
        classorder = self.dataset.aggregate_histogram(self.responseCol).keys().map(lambda number: ee.Number.parse(number))

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
            'features': self.dataset,
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
    
    def kFoldCV(self, nFolds):
        result = ee.ImageCollection(ee.List.sequence(0,nFolds-1).map(lambda fold: self._kFoldCV(fold)))
        return result
