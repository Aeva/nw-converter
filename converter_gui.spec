# -*- mode: python -*-

import os
import site

block_cipher = None

typelib_path = os.path.join(site.getsitepackages()[1], 'gnome', 'lib', 'girepository-1.0')

a = Analysis(['converter_gui.py', 'converter_gui.spec'],
             pathex=['C:\\Users\\Mym\\Downloads\\nw-converter'],
             binaries=[(os.path.join(typelib_path, tl), 'gi_typelibs') for tl in os.listdir(typelib_path)],
             datas=None,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='converter_gui',
          debug=False,
          strip=False,
          upx=True,
          console=True )
