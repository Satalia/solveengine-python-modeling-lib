# -*- coding: utf-8 -*-
"""
Setup for the Solver-Engine
"""

from distutils.core import setup

setup(
    name='SolveEngine',
    version='0.1',
    author="Karsten Lehmann",
    author_email="karsten@satalia.com",
    description="A library to model MILP/SAT problems and have them solved via the SolveEngine using the web API",
    keywords="SolveEngine MIP SAT Optimization",
    packages=['solveengine'],
    license='',
    url='https://github.com/AlexMSatalia/SolveEngine',
    download_url='https://github.com/AlexMSatalia/SolveEngine/archive/0.1.tar.gz',
    long_description=open('README.txt').read(),
)
