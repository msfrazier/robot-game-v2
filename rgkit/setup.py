#!/usr/bin/env python
'''
Run: ./setup.py register sdist upload
Check: ./setup.py checkdocs (pip install collective.checkdocs)
'''

from setuptools import setup

with open('README.rst') as readme_file:
    long_description = readme_file.read()

setup(
    name='rgkit',
    version='0.5.2',
    description='Game Engine for Robot Game',
    maintainer='Peter Wen',
    maintainer_email='peter@whitehalmos.org',
    url='https://github.com/RobotGame/rgkit',
    packages=['rgkit', 'rgkit.render'],
    package_data={'rgkit': ['bots/*.py', 'maps/*.py']},
    license='Unlicense',
    long_description=long_description,
    entry_points={
        'console_scripts': [
            'rgrun = rgkit.run:main',
            'rgmap = rgkit.mapeditor:main'
        ]
    },
)
