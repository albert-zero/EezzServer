from   distutils.core import setup
import py2exe
from   glob import glob

data_files = [("Microsoft.VC120.CRT", glob(r'C:\Program Files (x86)\Microsoft Visual Studio 12.0\VC\redist\x64\Microsoft.VC120.CRT\*.*'))]
includes   = ['bluetooth', 'Crypto', 'xml.etree', 'sqlite3']

py2exe_options = {
     'build' : {'build_base': 'dist/'},
     'py2exe': {
            'dist_dir': 'dist',
            'includes': includes,
            'packages': ['bluetooth', 'sqlite3']
     }
 }

setup (
    options    = py2exe_options,
    data_files = data_files,
    console    = ['eezz/server.py']
    )
