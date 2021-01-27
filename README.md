# Playground to analyze UCM configuration data

Tool looks for TAR files with a UCM config export in the project directory

Code is provided "as is". Use at your own risk.

Based on Python 3.8

To use the sample code:
* install Python from [python.org](https://www.python.org)
* create a virtual environment for Python to keep the module dependencies isolated.  
  IMO the most comfortable way to work with Python virtual environments is to use [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/).  
  I'm not sure whether/how that works on Windows.
  A possible fallback is to follow these steps: https://docs.python.org/3/tutorial/venv.html  
* Download all file of this repository to a project directory
* in that project directory install the project requirements with `pip install -r requirements.txt`.  
  If you created and activated a virtual environment before then the project requirements are not installed in the 
  context of your system Python installation but only in the context of your virtual environment