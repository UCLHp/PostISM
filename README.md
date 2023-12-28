# Post-ISM routine QA GUI  
Author: Alex Grimwood 2022/2023

## Description
GUI application written in python, designed for routine Post-ISM QA. Includes functionality for processing Logos acquisition files and for read-write to the PBT Physics Access QA database.

## Dependencies:
* See `requirements.txt` for Python dependencies.  
* PostISM application also requires spotanalysis as a submodule (https://github.com/UCLHp/spot-analysis).  
* `db_config.cfg` must be edited locally to to include the correct QA database credentials and location.  
* `logos_config.json` must also be updated with the correct chevron output consistency parameters should any of these change.  
* Compile using PyInstaller (see the `PostISM.spec` file as an example) to run as a local executable.

## Python Files
* `analyse.py` - processes data passed to the GUI and generates pdf reports.
* `checks.py` - checks data integrity before performing any analysis. called when "Check Session" button is pressed in the GUI. Warnings are raised in the GUI if data is invalid.
* `chevron.py` - chevron class, can be sed as a standalone tool for processing chevron data. Requires a valid logos_confi.json file.
* `database_df.py` - methods for reading chamber correction/calibration factors from the QA database, also for writing data to results and session tables for: chevron, Post-ISM output consistency and spot grid measurements. Graphic methods also included for data visualisation within GUI.  
* `gui.py` - specifies GUI layout (designed with PySimpleGUI).
* `main.py` - GUI compilation and I/O. Chamber dose calculated on the fly using `calc_metrics` method.
* `splash_screen.py` - required by PyInstaller to manage GUI application's splash screen.

## Other files
* `splash.jpg` - GUI splash screen picture.
* `cat.ico` - GUI icon pictures.
* `def_gradient_ratio.png` and `profiles_per_spot.png` - image files required by spotprofiles submodule.
* `requirements.txt` - python modules required to run codebase
* `db_config.cfg` - config file containing QA database parameters
* `PostISM.spec` - PyInstaller specification file example. Required to compile local executable using PyInstaller. Create a local copy of this repository and edit line 11 accordingly.
* `logos_config.json` - specif data required to analyse data collected from Logos acquisitions.
  * MeV: Chevron energy layers
  * h, SAD_X, SAD_Y, Chevron_WER, Target_WER, Target_l, LCW_half_width: optimised chevron model parameters (see commissioning report for further information).
  * D80_NIST: NIST PSTAR reference ranges for the energies listed in "MeV" field.
  * D80_TPS: UCLH reference ranges for the energies listed in "MeV" field (derived from water tank measurements).
  * D80_Baseline: Baseline chevron ranges acquired as part of commissioning for the energies listed in "MeV" field.
  * SpotE: energies delivered during spot grid measurements (not a part of chevron workflow).
