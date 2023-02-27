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

<h3 align="center">Invasive Tree Species mapping</h3>

  <p align="center">
    A 8-step workflow that uses time series satellite data (Sentinel-1, Sentinel-2 L1C and/or Sentinel-2 L2A) and Google Earth Engine to map invasive tree species.
    <br />
    <a href="https://github.com/Geethen/Invasive_Species_Mapping/blob/main/example_usuage/end_to_end_example.ipynb"><strong>Run through an end-to-end example»</strong></a>
    <br />
    <br />
    <a href="https://github.com/Geethen/Invasive_Species_Mapping/blob/main/example_usuage">View More Examples</a>
    ·
    <a href="https://github.com/Geethen/geeml/issues">Report Bug</a>
    ·
    <a href="https://github.com/Geethen/geeml/issues">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Basic Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project
This Github repository contains examples to make classification workflows easier. It includes functionality to create cloud-free image composites for multiple time steps. Despite the main focus on invasive tree species, the functionality that is provided is directly applicable to any classification workflow that relies on time series information from Sentinel-1 and Sentinel-2 alone or combined.

### Motivation
Classification workflows follow the same steps and use similar code, with the input (reference points) data usually the only thing changing. It therefore is sensible to provide this boiler plate code for more experienced programmers to build on or for more early-stage programmers to use as is and reduce/remove programming barriers to entry.

**Features**
* Create cloud-free regular image composites of Sentinel-2 (and Sentinel-1).
* Visualise and export intermediate and final inputs and outputs.
* Import refernce points into Google Earth Engine.
* Transform coordinates and add as additional covariates with topographic variables (for example, elevation, CHILI, slope and aspect).

<!-- GETTING STARTED -->
## Getting Started
In its current state, this repo is meant to be used from Google colab. As such the functionality can be used by cloning this repository. Refer to the [linked example](https://github.com/Geethen/Invasive_Species_Mapping/blob/main/example_usuage/end_to_end_example.ipynb) above for a guided demonstration.

For the [end-to-end example provided](https://github.com/Geethen/Invasive_Species_Mapping/blob/main/example_usuage/end_to_end_example.ipynb), the reference points (shapefile) is already uploaded to Google Earth Engine (GEE). However, if you need to upload your shapefile to GEE you could either [manually upload it](https://developers.google.com/earth-engine/guides/table_upload) or you could upload it by using the geeup package. An example using the geeup package can be found [here](https://github.com/Geethen/Invasive_Species_Mapping/blob/main/example_usuage/geeup_Simple_CLI_for_Earth_Engine_Uploads.ipynb).

<p align="right">(<a href="#top">back to top</a>)</p>


<!-- USAGE EXAMPLES -->
## Basic usage

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
   
  # Load python modules with preprocessing functions. 
    from timeSeriesFunctions import prepareTS
    from covariateFunctions import prepareCovariates
    from trainDataFunctions import prepareTrainingData
    from modelFitFunctions import prepareModel
    from metricFunctions import prepareMetrics
   ```

_For more examples, please refer to the [Example usuage folder](https://github.com/Geethen/Invasive_Species_Mapping/blob/main/example_usuage)_

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- ROADMAP -->
## Roadmap

- [ ] Add support for Landsat
- [ ] Add additional groups of covariates
- [ ] Add more examples

See the [open issues](https://github.com/Geethen/geeml/issues) for a full list of proposed features (and known issues).

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

The code provided here has been ported from code originally written by Glenn Moncrieff in GEE JavaScript.

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/Geethen/Invasive_Species_Mapping.svg?style=for-the-badge
[contributors-url]: https://github.com/Geethen/Invasive_Species_Mapping/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/Geethen/Invasive_Species_Mapping.svg?style=for-the-badge
[forks-url]: https://github.com/Geethen/Invasive_Species_Mapping/network/members
[stars-shield]: https://img.shields.io/github/stars/Geethen/Invasive_Species_Mapping.svg?style=for-the-badge
[stars-url]: https://github.com/Geethen/Invasive_Species_Mapping/stargazers
[issues-shield]: https://img.shields.io/github/issues/Geethen/Invasive_Species_Mapping.svg?style=for-the-badge
[issues-url]: https://github.com/Geethen/Invasive_Species_Mapping/issues
[license-shield]: https://img.shields.io/github/license/Geethen/Invasive_Species_Mapping.svg?style=for-the-badge
[license-url]: https://github.com/Geethen/Invasive_Species_Mapping/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/linkedin_username
[product-screenshot]: images/screenshot.png
