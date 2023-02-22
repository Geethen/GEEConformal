import ee


class prepareCovariates:
    def __init__(self, proj = 'EPSG:4326'):
        self.proj = proj
 
    def addRotatedCoords(self, ang):
        """
        //adds bands with coordinates rotated to account for spatial autocorrelation
        // Reference: Møller, A. B., Beucher, A. M., Pouladi, N., & Greve, M. H. (2020).  
        Oblique geographic coordinates as covariates for digital soil mapping. Soil, 6(2), 269-289.
        """
        ang = ee.Number(ang).multiply(3.141592653589793)
        ang = ee.Image(ang)
        xy = ee.Image.pixelCoordinates(ee.Projection(self.proj))
        z = xy.select('y').pow(2).add(xy.select('x').pow(2)).sqrt().multiply(
         ang.subtract(xy.select('y').divide(xy.select('x')).atan()).cos())
        return z
    
    def addCoordProperty(self, features):
        """
        This function adds coordinates to the points
        """
        def coords(feature):
            return feature.geometry().transform(proj = self.proj).coordinates()

        return features.map(lambda ft: ft.set('x', coords(ft).getNumber(0)).set('y', coords(ft).getNumber(1)))
                            
    def addTopoBands(self, image):
        """
        Adds SRTM elevation, CHILI, Topographic diversity, slope and aspect
        """
        
        # Load the SRTM elevation image.
        elevation = ee.Image("USGS/SRTMGL1_003").rename('elevation')
        # Load the CHILI images- proxies for microclimate
        chili = ee.Image("CSP/ERGo/1_0/Global/SRTM_CHILI").rename('chili')
        tpi =  ee.Image("CSP/ERGo/1_0/Global/SRTM_mTPI").rename('tpi')
        # Apply an algorithm to compute slope and aspect.
        slope = ee.Terrain.slope(elevation).rename('slope')
        aspect = ee.Terrain.aspect(elevation).rename('aspect')
                            
        return image.addBands([elevation, chili, tpi, slope, aspect])
