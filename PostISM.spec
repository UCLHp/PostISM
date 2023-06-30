# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

def get_pandas_path():
    import pandas
    pandas_path = pandas.__path__[0]
    return pandas_path

a = Analysis(['main.py'],
	pathex=['O:\protons\Work in Progress\AlexG\PostISM_Jig\test_repo\PostISM'],
	binaries=None,
	datas=[('*.png','.'),('*.ico','.'),('spotanalysis\\*','spotanalysis'),('db_config.cfg','.'),('logos_config.json','.')],
	hiddenimports=[],
	hookspath=None,
	runtime_hooks=None,
	excludes=None,
	win_no_prefer_redirects=None,
	win_private_assemblies=None,
	cipher=block_cipher)
			 
dict_tree = Tree(get_pandas_path(), prefix='pandas', excludes=["*.pyc"])
a.datas += dict_tree
a.binaries = filter(lambda x: 'pandas' not in x[0], a.binaries)
			 
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
      a.scripts,
	  a.binaries,
	  a.zipfiles,
	  a.datas,
      name='PostISM_V0.exe',
      debug=False,
      strip=None,
      upx=True,
	  icon='cat.ico',
      console=True )
