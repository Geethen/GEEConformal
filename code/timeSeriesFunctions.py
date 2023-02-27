import ee

class prepareTS:
    def __init__(self, Date_Start,Date_End,day_int,study_area,CLOUD_THRESH,BANDS):
        """Pre-process an image collection in preparration for a time-series problem
        
        Args: 
            Date_Start (ee.Date): start date of time series
            Date_End (ee.Date): end date of time series
            day_int (int): number of days to summarise in each image e.g 30 days = 12 images per year
            study_area (ee.Geometry): area of interest
            CLOUD_THRESH (int): cloud probabillity threshold
            BANDS (list): which bands to keep.

        Returns:
            ee.ImageCollection: image collection with cloud probability band, summarised to day_int, and gap filled.

        # Example Usuage
        
        # Start and end dates for time series
        Date_Start = ee.Date('2017-01-01');
        Date_End = ee.Date('2017-12-31');

        # how many days to summarise in each image e.g 30 days = 12 images per year
        day_int = 30; #step size

        # cloud probabillity threshold
        CLOUD_THRESH=30

        # which bands to keep
        BANDS = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6','B7', 'B8', 'B8A', 'B9', 'B11','B12', 'ndvi','ndwi','ndre','nbr','evi']
        
        # Point of interest (in this case, a point in South Africa)
        aoi = ee.Geometry.Point([25.181, -28.490])
        
        # add cloud probability band to sentinel-2, compute a composite image for interval (day_int), and perform gap filling.
        test = prepareTS(Date_Start,Date_End,day_int,aoi,CLOUD_THRESH,BANDS)\
        .timeSeries(satellite = 'S2', s2_level = 2)

        """
    
        self.Date_Start = Date_Start
        self.Date_End = Date_End
        self.day_int = day_int
        self.study_area = study_area
        self.CLOUD_THRESH = CLOUD_THRESH
        self.BANDS = BANDS
    
    
    def joinS2(self, s2_level):
        """
        Add cloud probability band to sentinel2

        Args:
            s2_level (int): Either 1 or 2. level 1 or 2 sentinel 2 data

        Returns:
            ee.ImageCollection: image collection with cloud probability band
        """
        self.s2_level = s2_level
        # Join the S2 and S2cloud collections.
        innerJoin = ee.Join.inner()
  
        # Specify an equals filter for image timestamps.
        filterIDEq = ee.Filter.equals(**{
                       'leftField': 'system:index',
                       'rightField': 'system:index'
                    })
        if s2_level == 1:
            # level 1 s2 data
            s2 = ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
        elif s2_level == 2:
            # level 2 s2 data
            s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")

        # level 1 s2 data
        S2_nocloud = s2\
        .filterBounds(self.study_area)\
        .filterDate(self.Date_Start, self.Date_End)

        # S2cloud prob data
        S2_cloud = ee.ImageCollection("COPERNICUS/S2_CLOUD_PROBABILITY")\
        .filterBounds(self.study_area)\
        .filterDate(self.Date_Start, self.Date_End)
  
        innerJoinedS2 = innerJoin.apply(S2_nocloud, S2_cloud, filterIDEq)
  
        # Map a function to merge the results in the output FeatureCollection
        joinedS2 = innerJoinedS2.map(lambda feature: ee.Image.cat(feature.get('primary'), feature.get('secondary')))    
        return ee.ImageCollection(joinedS2)
    
    def joinS1S2(self, S1_filled, S2_filled):
        """Joins Sentinel 1 and Sentinel 2 data

        Args:
            S1_filled (ee.ImageCollection): Sentinel 1 data
            S2_filled (ee.ImageCollection): Sentinel 2 data

        Returns:
            ee.ImageCollection: image collection with Sentinel 1 and Sentinel 2 data
        """
        # Join S1 and S2
        inner_join = ee.Join.inner()

        # Specify an equals filter for image timestamps.
        filter_S12 = ee.Filter.equals(leftField='system:time_start', rightField='system:time_start')

        inner_joined_S12 = inner_join.apply(S2_filled, S1_filled, filter_S12)

        # Map a function to merge the results in the output ImageCollection.
        joined_S12 = inner_joined_S12.map(lambda feature: ee.Image.cat(feature.get('primary'), feature.get('secondary')))

        S12_final = ee.ImageCollection(joined_S12)

        return S12_final

    def _createS2Mosaic(self, date_begin, s2_level = None):
        """Creates a Sentinel 2 mosaic for every date in the sequence.

        Returns:
            An image with the Sentinel 2 mosaic for the specified date range.
            Returns an ee.Image object.
        """
        self.s2_level = s2_level

        # start and end dates for this image
        start = ee.Date(date_begin)
        end = ee.Date(date_begin).advance(self.day_int, 'day')
        date_range = ee.DateRange(start, end)

        # create collection each time step
        S2_collection = (self.joinS2(self.s2_level).filterDate(date_range)
                        .filterBounds(self.study_area)
                        .map(lambda image: self.shadow_cloud_mask(image))
                        .map(lambda image: image.divide(10000))
                        .map(lambda image: image.addBands(
                            image.normalizedDifference(['B8', 'B4']).rename(['ndvi'])))
                        .map(lambda image: image.addBands(
                            image.normalizedDifference(['B8', 'B5']).rename(['ndre'])))
                        .map(lambda image: image.addBands(
                            image.normalizedDifference(['B8', 'B11']).rename(['ndwi'])))
                        .map(lambda image: image.addBands(
                            image.normalizedDifference(['B8', 'B12']).rename(['nbr'])))
                        .map(lambda image: image.addBands(
                            image.expression(
                                '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))', {
                                    'NIR': image.select('B8'),
                                    'RED': image.select('B4'),
                                    'BLUE': image.select('B2')
                                }).rename(['evi'])))
                        .select(self.BANDS))

        # mosaic collection into a single image
        # if we have multiple obs, we keep the image with the highest ndvi
        S2_mosaic = S2_collection.qualityMosaic('ndvi')
        S2_mosaic_bands = self.BANDS

        # need to deal with cases in which we have no image for the time period
        # if we do have an image, we just keep the mosaic
        # if we don't have an image we insert an empty image with the same band names
        S2 = ee.Algorithms.If(S2_collection.size(),
                               S2_mosaic,
                               ee.ImageCollection(ee.List(S2_mosaic_bands).map(lambda band: ee.Image()))\
                               .toBands()\
                               .rename(S2_mosaic_bands))

        # return the image, with the date set
        return ee.Image(S2).set({'system:time_start': start})
        
    def _createS1Mosaic(self, date_begin):
        """Creates a Sentinel 1 mosaic for every date in the sequence.

        Args:
            date_begin (ee.Date): The date to begin the mosaic.

        Returns:
            An image with the Sentinel 1 mosaic for the specified date range.
            Returns an ee.Image object.
        """
        #start and end dates for this image
        start = ee.Date(date_begin)
        end = ee.Date(date_begin).advance(self.day_int, 'day')
        date_range = ee.DateRange(start, end)
        
        #create collection each time step
        S1_collection = ee.ImageCollection("COPERNICUS/S1_GRD") \
            .filterDate(date_range) \
            .filterBounds(self.study_area) \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')) \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
            .filterMetadata('instrumentMode','equals','IW') \
            .filterMetadata('orbitProperties_pass','equals','ASCENDING') \
            .map(lambda image: image.addBands(image.select(['VH']).divide(image.select(['VV'])).rename(['VH/VV']))) \
            .select(self.BANDS)
        
        #mosaic collection into a single image
        #if we have multiple obs we take mean
        S1_mosaic = S1_collection.mean()
        S1_mosaic_bands = self.BANDS
        
        #need to deal with cases in which we have no image for the time period
        #if we do have an image, we just keep the mosaic
        #if we dont have an image we insert an empty image with the same bands names
        S1 = ee.Algorithms.If(S1_collection.size(),
                               S1_mosaic,
                               ee.ImageCollection(ee.List(S1_mosaic_bands) \
                                                  .map(lambda band: ee.Image())) \
                               .toBands() \
                               .rename(S1_mosaic_bands))
        
        #return the image, with the date set
        return ee.Image(S1).toFloat().set({'system:time_start': start})
    
    def createMosaic(self, satellite: str, s2_level: int = None):
        """Creates a Sentinel-1 or Sentinel-2 mosaic for every date in the sequence.
        
        Args:
            satellite (str): The satellite to use. Either 'S2' or 'S1'.
            s2_level (int): The Sentinel 2 level to use. Either 1, 2, or 3.
            
        Returns:
            An image with the Sentinel 1/2 mosaic for the specified date range."""
        self.s2_level = s2_level

        # setup a sequence of dates
        n_days = self.Date_End.difference(self.Date_Start,'day').round()
        dates = ee.List.sequence(0, n_days, self.day_int)
        dseq = dates.map(lambda n: self.Date_Start.advance(n,'day'))

        if satellite == 'S2':
            mosaic = dseq.map(lambda d: self._createS2Mosaic(d, self.s2_level))
        elif satellite == 'S1':
            mosaic = dseq.map(lambda d: self._createS1Mosaic(d))

        return mosaic
    
    def shadow_cloud_mask(self, image):
        """Creates a cloud and shadow mask for a Sentinel 2 image.

        Args:
            image (ee.Image): The Sentinel 2 image.

        Returns:
            A Sentinel-2 image with the cloud and shadow masked.
        """
    
        def potential_shadow(cloud_height):
            cloud_height = ee.Number(cloud_height)

            # shadow vector length
            shadow_vector = zenith.tan().multiply(cloud_height)

            # x and y components of shadow vector length
            x = azimuth.cos().multiply(shadow_vector).divide(nominal_scale).round()
            y = azimuth.sin().multiply(shadow_vector).divide(nominal_scale).round()

            # affine translation of clouds
            cloud_shift = cloud_mask.changeProj(cloud_mask.projection(), cloud_mask.projection().translate(x, y))

            return cloud_shift

        # select a cloud mask
        cloud_mask = image.select(['probability'])

        img = image.select(['B1','B2','B3','B4','B6','B8A','B9','B10', 'B11','B12'],
                 ['aerosol', 'blue', 'green', 'red', 'red2','red4','h2o', 'cirrus','swir1', 'swir2'])\
                 .divide(10000).addBands(image.select('QA60'))\
                 .set('solar_azimuth',image.get('MEAN_SOLAR_AZIMUTH_ANGLE'))\
                 .set('solar_zenith',image.get('MEAN_SOLAR_ZENITH_ANGLE'))

        # make sure it is binary (i.e. apply threshold to cloud score)
        cloud_score_threshold = self.CLOUD_THRESH
        cloud_mask = cloud_mask.gt(cloud_score_threshold)

        # solar geometry (radians)
        azimuth = ee.Number(img.get('solar_azimuth')).multiply(3.14159265359).divide(180.0).add(ee.Number(0.5).multiply(3.14159265359))
        zenith  = ee.Number(0.5).multiply(3.14159265359).subtract(ee.Number(img.get('solar_zenith')).multiply(3.14159265359).divide(180.0))

        # find potential shadow areas based on cloud and solar geometry
        nominal_scale = cloud_mask.projection().nominalScale()
        cloud_heights = ee.List.sequence(500,4000,500)
        potential_shadow_stack = cloud_heights.map(lambda ch: potential_shadow(ch))
        potential_shadow = ee.ImageCollection.fromImages(potential_shadow_stack).max()

        # shadows are not clouds
        potential_shadow = potential_shadow.And(cloud_mask.Not())

        # (modified) dark pixel detection
        dark_pixels = img.normalizedDifference(['green', 'swir2']).gt(0.25)

        # shadows are dark
        shadows = potential_shadow.And(dark_pixels)
        cloud_shadow_mask = shadows.Or(cloud_mask)

        return image.updateMask(cloud_shadow_mask.Not())
    
    def timeSeries(self, satellite: str, s2_level: int = None):
        """Returns a function that takes an image and applies gap-filling.

        Args:
            composites: A collection of composite images.
                Must be an ee.ImageCollection object.
            satellite: The satellite for which to create the gap-filling function. Must be either 'S2' or 'S1'.
            s2_level: The level of Sentinel 2 data to use. Must be either 1 or 2. This corresponds to L1C or L2A respectively.

        Returns:
            A function that applies gap-filling to an image.
            The function takes an ee.Image object as input and returns an ee.Image object.
        """
        self.s2_level = s2_level
        if satellite == 'S2':
            composites = ee.ImageCollection(self.createMosaic('S2', self.s2_level))
        elif satellite == 'S1':
            composites = ee.ImageCollection(self.createMosaic('S1'))
        
        def gapFillS2(image: ee.Image) -> ee.Image:
            """Applies gap-filling to an image.

            Args:
                image: The image to which to apply gap-filling.
                    Must be an ee.Image object.

            Returns:
                The image with gap-filling applied.
                Returns an ee.Image object.
            """
            currentDate = ee.Date(image.get('system:time_start'))
            # 6 month median
            med6Image = composites.filterDate(
                currentDate.advance(-3, 'month'), 
                currentDate.advance(3, 'month')
            ).median()
            # 2 month median
            med2Image = composites.filterDate(
                currentDate.advance(-1, 'month'), 
                currentDate.advance(1, 'month')
            ).median()
            # replace all masked values
            medImage = med6Image.where(med2Image, med2Image)
            return medImage.where(image, image)
        
        def gapFillS1(image: ee.Image) -> ee.Image:
            """Applies gap-filling to an image.

            Args:
                image: The image to which to apply gap-filling.
                    Must be an ee.Image object.

            Returns:
                The image with gap-filling applied.
                Returns an ee.Image object.
            """
            currentDate = ee.Date(image.get('system:time_start'))
            # 2 week mean
            mean2Image = composites.filterDate(
                currentDate.advance(-2, 'week'), 
                currentDate.advance(2, 'week')
            ).mean()
            # 8 week mean
            mean8Image = composites.filterDate(
                currentDate.advance(-8, 'week'), 
                currentDate.advance(8, 'week')
            ).mean()
            # replace all masked values
            meanImage = mean2Image.unmask(mean8Image)
            return meanImage.set({'system:time_start': currentDate})
          
        if satellite == 'S2':
            filled = ee.ImageCollection(composites.map(lambda image: gapFillS2(image))).toBands()
        if satellite == 'S1':
            filled = ee.ImageCollection(composites.map(lambda image: gapFillS1(image))).toBands()

        return filled.regexpRename('^(.{0})', 'band')