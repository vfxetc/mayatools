import os
from subprocess import check_call

from setuptools import setup, find_packages
from distutils.command.build import build as default_build



class build(default_build):

    def run(self):
        # Quickly disable the `make` for Mark Media (who does not need the compiled plugins).
        if os.environ.get('MAYATOOLS_SETUP_MAKE'):
            check_call(['make'])
        default_build.run(self)


setup(
    name='mayatools',
    version='0.1-dev',
    description='Collection of general tools and utilities for working in and with Maya.',
    url='https://github.com/westernx/mayatools',
    
    packages=find_packages(exclude=['build*', 'tests*']),
    include_package_data=True,
    
    author='Mike Boers',
    author_email='mayatools@mikeboers.com',
    license='BSD-3',
    
    cmdclass={'build': build},

    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
