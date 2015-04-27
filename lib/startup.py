# set this as PYTHONSTARTUP environment variable
import sys
from os import path
from subprocess import call

# find kivy's python and execute kivy.bat

path_kivy_bat = path.join(path.dirname(path.dirname(sys.executable)), "kivy.bat")
call(path_kivy_bat)
