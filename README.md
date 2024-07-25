<div id="top"></div>

<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]


<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/Geethen/geeml">
    <img src="./images/logo2_GEEML.png" alt="Logo" width="400" height="400">
  </a>

<h3 align="center">Uncertainty Quantification for Google Earth Engine</h3>

  <p align="center">
    Quantify uncertainty using conformal prediction for classification and regression tasks in Google Earth Engine. Examples for 1) tree canopy height estimation using conformal quantile regression using Planet NICFI and GEDI data, 2) uncertainty quantification for Google Dynamic World landcover data and 3) for invasive tree species mapping.
    <br />
    <a href="https://github.com/Geethen/GEEConformal/blob/main/example_usuage/Invasive%20Species%20Mapping/IAS_mapping_wUQ.ipynb"><strong>Run through an end-to-end example»</strong></a>
    <br />
    <br />
    <a href="https://github.com/Geethen/GEEConformal/tree/main/example_usuage">View More Examples</a>
    ·
    <a href="https://github.com/Geethen/GEEConformal/issues">Report Bug</a>
    ·
    <a href="https://github.com/Geethen/GEEConformal/issues">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project<a></li>
    <li><a href="#getting-started">Getting Started<a></li></li>
    <li><a href="#usuage-examples">Usuage Examples</a><ul>
        <li><a href="#javascript">JavaScript</a></li>
        <li><a href="#python">Python</a></li></ul>
    </li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project
This Github repository contains the code for the [arxiv](https://arxiv.org/pdf/2401.06421), [peer-reviewed](https://www.nature.com/articles/s41598-024-65954-w) and [ICLR 24 short version](https://ml-for-rs.github.io/iclr2024/camera_ready/papers/6.pdf) research paper "Uncertainty quantification for probabilistic machine learning in earth observation using conformal prediction". It includes functionality to quantify uncertainty using conformal prediction,  create gap filled cloud-free image composites for multiple time steps and spatial cross validation.

For a more gentle introduction and example use of conformal prediction for Dynamic world refer to [this medium blogpost](https://medium.com/@coachgeets/uncertainty-quantification-in-google-earth-engine-using-conformal-prediction-5e0dd3850564)

### Motivation
Uncertainty Quantification (UQ) provides information on prediction quality and can allow for comparisons and itegration of datasets. Conformal prediction is currently the only UQ framework that can provide pixel wise uncertainty information with valid coverage (i.e., if a 0.9 confidence level is specified, alpha = 0.1, the prediction regions will contain the actual value with a 90% probability).

**Features**
* GEE-Native Conformal classifier and regressor support
* Support for GEE-JS and GEE-Python API
* Create cloud-free image composites of Sentinel-2 and gap-free composites for Sentinel-1.
* Examples to demonstrate end-to-end workflows that include, visualisation, API-based imports and exports, coomputation of additional topographic and coordinate-transformed variables, model fitting, and inference.
* Spatial cross-validation.

<!-- GETTING STARTED -->
## Getting Started
In its current state, this repo is meant to be used from Google colab. As such the functionality can be used by cloning this repository. Refer to the [linked example](https://github.com/Geethen/GEEConformal/blob/main/example_usuage/Invasive%20Species%20Mapping/IAS_mapping_wUQ.ipynb) above for a guided demonstration.

For the [end-to-end example provided](https://github.com/Geethen/GEEConformal/blob/main/example_usuage/Invasive%20Species%20Mapping/IAS_mapping_wUQ.ipynb), the reference points (shapefile) are already uploaded to Google Earth Engine (GEE). However, if you need to upload your own shapefile to GEE you could either [manually upload it](https://developers.google.com/earth-engine/guides/table_upload) or you could upload it by using the geeup package. An example using the geeup package can be found [here](https://github.com/Geethen/GEEConformal/blob/main/example_usuage/gee_shp_upload.ipynb).

<p align="right">(<a href="#top">back to top</a>)</p>


<!-- USAGE EXAMPLES -->
<!-- JAVASCRIPT -->
## JavaScript

The repository with all GEE conformal JS code can be accessed using this link: [https://code.earthengine.google.com/?accept_repo=users/geethensingh/conformal](https://code.earthengine.google.com/?accept_repo=users/geethensingh/conformal)

The repo contains code to calibrate, evaluate and run inference using the calibrated conformal classifier or regressor for both feature and imge collections. Demos are provided for each script.

Assuming a model has already been trained for a classification or regression task and there is an out-of-sample dataset available for calibrating and evaluating a conformal predictor, there are three steps to quantify uncertainty with a guranteed coverage (as shown below).

Note: There are distinct modules for ImageCollections and FeatureCollections. The inference module is the only shared module.

Step 
1) Calibrate a conformal predictor. [Example usuage](https://code.earthengine.google.com/265062792213a03c463e35ad7c051404)
 ```javascript
 //import conformal classifier calibration functions
var calFunctions = require('users/geethensingh/conformal:calibrateConformalFeatureClassifier.js');

// Configuration parameters
var ALPHA = 0.1; // 1-ALPHA corresponds to required coverage. For example, 0.1 for 90% coverage
var SCALE = 10; // Used to compute Eval metrics
var SPLIT = 0.8; // Split used for calibration and test data (for example, 0.8 corresponds to 80% calibration data)
var LABEL = 'label'; //band name for reference label band

// points refer to an out-of-sample featurecollection (not used during training), that contains, as properties,
1) the pseudo-probability of each candidate class
2) the reference label (called 'label' in this case). It should be zero-indexed
3) a value from the randomColumn function used to split the data into a calibration and evaluation dataset based on the user specified SPLIT

var result = calFunctions.calibrate(points, bands, ALPHA, SCALE, SPLIT, LABEL, 'demoDW_15112023');
print(result);//returns qhat value to be used during evaluation and inference (uncertainty quantification)
 ```

2) Evaluate conformal predictor. [Example usuage](https://code.earthengine.google.com/6305e83f23199c63b480657f811278b1)
```javascript
//import conformal classifier evaluation functions
var evalFunctions = require('users/geethensingh/conformal:evaluateConformalFeatureClassifier.js');

// Configuration parameters
var QHAT = 0.06450596045364033; // from calibration script
var SCALE = 10; // Used to compute Eval metrics
var SPLIT = 0.8; // Split used for calibration and test data (for example, 0.8 corresponds to 80% calibration data, 20% evaluation data)

// points refer to the out-of-sample featurecollection (not used during training but the same collection provided in the calibration stage), that contains, as properties,
1) the pseudo-probability of each candidate class
2) the reference label (called 'label' in this case). It should be zero-indexed
3) a value from the randomColumn function used to split the data into a calibration and evaluation dataset based on the user specified SPLIT

var result = evalFunctions.evaluate(points, bands, QHAT, SCALE, SPLIT, 'demoDW_15112023');
print(result);// This will return the empirical coverage and the average set size

 ```

3) Quantify uncertainty for a test image [Example usuage](https://code.earthengine.google.com/7a891a0f960680c20a84503b245553fe)
```javascript
// Import conformal classifier inference functions
var infFunctions = require('users/geethensingh/conformal:inferenceConformalImageClassifier.js');

// Configuration parameters
var QHAT = 0.06067845112312009; // From calibration script

// Uncertainty Quantification: inference function is mapped over every dynamic world image in the collection
//dwp refers to an ee.Image with a probability band for each candidate band. if using an ee.Classifier, use arrayFlatten([[bandNames]])
var result = infFunctions.inference(dwp, bands, QHAT);
 ```
 <p align="right">(<a href="#top">back to top</a>)</p>

<!-- PYTHON -->
## Python

The GEE-Python conformal classifiers can be used in a similar fashion to the JavaScript modules and must be loaded by cloning the github repo (as shown below)

   ```python
# Install and import packages
%pip install watermark geemap geeml -q

!git clone https://github.com/Geethen/Invasive_Species_Mapping.git

import sys
sys.path.insert(0,'/content/Invasive_Species_Mapping/code')

  # Authenticate GEE
  ee.Authenticate()
  # Initialize GEE with high-volume end-point
  ee.Initialize(opt_url='https://earthengine-highvolume.googleapis.com')
   ```

_For more examples (Includes three case studies from the research paper), please refer to the [Example usuage folder](https://github.com/Geethen/GEEConformal/tree/main/example_usuage)_

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- ROADMAP -->
## Roadmap

- [ ] Add support for RAPS and APS conformal prediction
- [ ] Add support for cloud and shadow masking using CloudScore+
- [ ] Add support for mondrian conformal prediction
- [ ] Add more examples

See the [open issues](https://github.com/Geethen/GEEConformal/issues?q=is%3Aissue+is%3Aopen+sort%3Aupdated-desc) for a full list of proposed features (and known issues).

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Glenn Moncrieff - [@Glennwithtwons](https://twitter.com/Glennwithtwons)

Geethen Singh - [@Geethen](https://twitter.com/Geethen) - geethen.singh@gmail.com

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [Saeon](https://www.saeon.ac.za/)
* [University of Stellenbosch](https://www.sun.ac.za/)
* [University of Cape Town](https://www.uct.ac.za/)

The Invasive Species Mapping code provided here has been ported from code originally written by Glenn Moncrieff in GEE JavaScript.

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/Geethen/GEEConformal.svg?style=for-the-badge
[contributors-url]: https://github.com/Geethen/GEEConformal/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/Geethen/GEEConformal.svg?style=for-the-badge
[forks-url]: https://github.com/Geethen/GEEConformal/network/members
[stars-shield]: https://img.shields.io/github/stars/Geethen/GEEConformal.svg?style=for-the-badge
[stars-url]: https://github.com/Geethen/GEEConformal/stargazers
[issues-shield]: https://img.shields.io/github/issues/Geethen/GEEConformal.svg?style=for-the-badge
[issues-url]: https://github.com/Geethen/GEEConformal/issues
[license-shield]: https://img.shields.io/github/license/Geethen/GEEConformal.svg?style=for-the-badge
[license-url]: https://github.com/Geethen/GEEConformal/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/geethen-singh-a06660106
[product-screenshot]: images/screenshot.png
