The repository with all GEE conformal JS code can be accessed using this link: [https://code.earthengine.google.com/?accept_repo=users/geethensingh/conformal](https://code.earthengine.google.com/?accept_repo=users/geethensingh/conformal)

The repo contains code to calibrate, evaluate and run inference using the calibrated conformal classifier or regressor. Demos are provided for each script.

## Basic usage

   ```javascript
// Example code to calibrate a conformal classifier for a feature collection

//import conformal classifier calibration functions
var calFunctions = require('users/geethensingh/conformal:calibrateConformalFeatureClassifier.js');

// Configuration parameters
var ALPHA = 0.1; // 1-ALPHA corresponds to required coverage. For example, 0.1 for 90% coverage
var SCALE = 10; // Used to compute Eval metrics
var SPLIT = 0.8; // Split used for calibration and test data (for example, 0.8 corresponds to 80% calibration data)
var LABEL = 'label'; //band name for reference label band
// ****************************//
// Data preparation

// Create a single polygon with a global extent
var globalBounds = ee.Geometry.Polygon([-180, 90, 0, 90, 180, 90, 180, -90, 10, -90, -180, -90], null, false);

// List of probability band names
var bands = ee.List(['water', 'trees', 'grass', 'flooded_vegetation',
'crops', 'shrub_and_scrub', 'built', 'bare', 'snow_and_ice']);

var dwl = ee.ImageCollection('projects/nina/GIS_synergy/Extent/DW_global_validation_tiles');
// var dwl = ee.ImageCollection('projects/ee-geethensingh/assets/UQ/dwTest_labels_4326');
var dwLabels = dwl
  .select([1], ['label'])//Select reference label band
  .map(function(img){//remove unmarked up areas and extra-class
    return ee.Image(img.updateMask(img.gt(0).and(img.lt(10))).subtract(1).copyProperties(img))
    //hacky method to edit image property
    .set('joinindex', img.rename(img.getString('system:index')).regexpRename('^[^_]*_', '').bandNames().getString(0));
  })
  
// var dwp = ee.ImageCollection("projects/ee-geethensingh/assets/UQ/dwTest_probs_4326");
var dwp = ee.ImageCollection("projects/ee-geethensingh/assets/UQ/DW_probs");
var dwp = dwp.map(function(img){//rename bands, mask 0 pixels
    return ee.Image(img.rename(bands).selfMask()).copyProperties(img)
    //hacky method to edit image property
    .set('joinindex', img.select([0]).rename(img.getString('id_no')).regexpRename('^[^_]*_', '').bandNames().getString(0));
  });
  
// Join label collection and probability collection on their 'joinindex' property.
// The propertyName parameter is the name of the property
// that references the joined image.
function indexJoin(collectionA, collectionB, propertyName) {
  var joined = ee.ImageCollection(ee.Join.saveFirst(propertyName).apply({
    primary: collectionA,
    secondary: collectionB,
    condition: ee.Filter.equals({
      leftField: 'joinindex',
      rightField: 'joinindex'})
  }));
  // Merge the bands of the joined image.
  return joined.map(function(image) {
    return image.addBands(ee.Image(image.get(propertyName)));
  });
}

var dwCombined = indexJoin(dwLabels, dwp, 'probImage');

// Get a stratified sample of each of 9 classes using the label band.
var data = ee.Image(dwCombined.first());

// Sample 600 points
var points = ee.FeatureCollection(data
.stratifiedSample({numPoints:100, classBand:'label', region:data.geometry(100),
scale:10, seed:42, geometries: true})).randomColumn({seed: 42});//add random column;

var result = calFunctions.calibrate(points, bands, ALPHA, SCALE, SPLIT, LABEL, 'demoDW_15112023');
print(result);
   ```