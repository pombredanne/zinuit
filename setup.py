from setuptools import setup, find_packages
import re, ast

# get version from __version__ variable in zinuit/__init__.py
_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

with open('zinuit/__init__.py', 'rb') as f:
	version = str(ast.literal_eval(_version_re.search(
		f.read().decode('utf-8')).group(1)))

setup(
	name='zinuit',
	description='Web based Integrated Enterprise Information System (IEIS)',
	author='Alphamonak Solutions',
	author_email='info@alphamonak.com',
	version=version,
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
	entry_points='''
[console_scripts]
zinuit=zinuit.cli:cli
''',
)
