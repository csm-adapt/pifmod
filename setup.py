try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

config = {
	'description': 'Utility to modify a Citrine PIF record.',
	'author': 'Branden Kappes',
	'url': 'https://github.com/csm-adapt/pifmod',
	'download_url': 'https://github.com/csm-adapt/pifmod',
	'author_email': 'bkappes@mines.edu',
	'version': '0.1',
	'install_requires': [
		'nose',
		'pypif'],
	'packages': ['pifmod'],
	'scripts': ['bin/pifmod'],
	'name': 'pifmod'
}
setup(**config)
