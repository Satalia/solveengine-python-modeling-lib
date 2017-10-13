# -*- coding: utf-8 -*-
"""
Setup for the Solver-Engine
"""

#from distutils.core import setup
from setuptools import setup

setup(
    name='SolveEngine',
    version='0.3',
    author="Karsten Lehmann",
    install_requires=open("requirements.txt", "r").read().split("\n"),
    author_email="karsten@satalia.com",
    description="A library to model MILP/SAT problems and have them solved via the SolveEngine using the web API",
    keywords="SolveEngine MIP SAT Optimization",
    packages=['solveengine', 'solveengine/examples'],
    license='',
    url='https://github.com/Satalia/solveengine-python-modeling-lib',
    download_url='https://github.com/Satalia/solveengine-python-modeling-lib/archive/0.3.tar.gz'
)

