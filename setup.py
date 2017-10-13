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
    author_email="karsten@satalia.com",
    description="A library to model MILP/SAT problems and have them solved via the SolveEngine using the web API",
    keywords="SolveEngine MIP SAT Optimization",
    packages=['solveengine', 'solveengine/examples'],
    license='',
    url='https://github.com/Satalia/solveengine-python-modeling-lib',
    download_url='https://github.com/Satalia/solveengine-python-modeling-lib/archive/0.3.tar.gz',
    install_requires=['beautifulsoup4>=4.6.0',
                      'certifi>=2017.7.27.1',
                      'chardet>=3.0.4',
                      'enum>=0.4.6',
                      'google>=1.9.3',
                      'google.api>=0.1.11',
                      'grpc>=0.3.post19',
                      'grpcio>=1.3.5',
                      'grpcio-tools>=1.3.5',
                      'idna>=2.6',
                      'msgpack-python>=0.4.8',
                      'protobuf>=3.3.0',
                      'requests>=2.18.4',
                      'six>=1.10.0',
                      'urllib3>=1.22']
)

