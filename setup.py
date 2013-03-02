from setuptools import setup, find_packages, Extension


setup(
    name='mayatools',
    version='0.1-dev',
    description='Collection of general tools and utilities for working in and with Maya.',
    url='https://github.com/westernx/mayatools',
    
    packages=find_packages(),
    
    author='Mike Boers',
    author_email='mayatools@mikeboers.com',
    license='BSD-3',
    
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],

    ext_modules=[
        Extension('mayatools.fluids.core', ['mayatools/fluids/core.c']),
    ],
)
