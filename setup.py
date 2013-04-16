#!/usr/bin/env python

from setuptools import setup

_description = 'Rebuild iTunesDB with libgpod',

setup(
    name='ItdbRebuild',
    version='0.1.0',
    license='MIT Apache BSD',
    url='https://jordan.yelloz.me/',
    author='Jordan Yelloz',
    author_email='jordan@yelloz.me',
    description=_description,
    long_description=_description,
    platforms='any',
    packages=['itdb_rebuild'],
    entry_points={
        'console_scripts': [
            'itdb-rebuild = itdb_rebuild:main',
        ],
    },
    install_requires=[
        'distribute',
        'argparse',
        'mutagen',
    ],
)
