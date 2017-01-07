# reference:
# - http://py2exe.org/index.cgi/Tutorial
# - https://gmigdos.wordpress.com/2014/06/29/how-to-bundle-python-gtk3-apps-on-windows-with-py2exe/

import os
import sys
import glob
import site
import shutil
from distutils.core import setup
import py2exe

dist_dir = os.path.join(os.getcwd(), 'dist')
if os.path.isdir(dist_dir):
     shutil.rmtree(dist_dir)
os.makedirs(dist_dir)

gnome_path = os.path.join(site.getsitepackages()[1], "gnome") 
gnome_resources = [
    'etc',
    'lib\\gtk-3.0', 'lib\\girepository-1.0', 'lib\\gio', 'lib\\gdk-pixbuf-2.0',
    'share\\glib-2.0', 'share\\fonts', 'share\\icons', 'share\\themes\\Default',
    'share\\themes\\HighContrast'
]
for path in glob.glob(os.path.join(gnome_path, "*.dll")):
    gnome_resources.append(os.path.split(path)[-1])

def bundle(resource):
    src_path = os.path.join(gnome_path, resource)
    dest_path = os.path.join(dist_dir, resource)
    assert os.path.exists(src_path)
    if os.path.isdir(src_path):
        shutil.copytree(src_path, dest_path)
    else:
        shutil.copy(src_path, dest_path)
            
sys.path.append(dist_dir)
map(bundle, gnome_resources)

# note, swap "console" and "windows" below to determine if a console
# window is to be shown
setup(console=['logger.py'], options={
    'py2exe': {
        'includes' : ['gi', 'PIL.Image'],
        'packages': ['gi', 'PIL'],
        'dll_excludes' : ['libgstreamer-1.0-0.dll',
                          'api-ms-win-core-processthreads-l1-1-2.dll',
                          'api-ms-win-core-sysinfo-l1-2-1.dll',
                          'api-ms-win-core-errorhandling-l1-1-1.dll',
                          'api-ms-win-core-profile-l1-1-0.dll',
                          'api-ms-win-core-libraryloader-l1-2-0.dll',
        ],
    }
})
