#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Note: To use the 'upload' functionality of this file, you must:
#   $ pip install twine

import io
import os
import sys
from shutil import rmtree

from setuptools import find_packages, setup, Command
import pip

# Save ~200ms on script startup time
# See https://github.com/ninjaaron/fast-entry_points
import fastentrypoints

# Package meta-data.
NAME = 'brotab'
DESCRIPTION = "Control your browser's tabs from the command line"
URL = 'https://github.com/balta2ar/brotab'
EMAIL = 'baltazar.bz@gmail.com'
AUTHOR = 'Yuri Bochkarev'


# What packages are required for this module to be executed?
REQUIRED = [
    # 'requests', 'maya', 'records',
]
# requirements = list(pip.req.parse_requirements(
#     'requirements.txt', session=pip.download.PipSession()))
# REQUIRED = [requirement.name for requirement in requirements]
REQUIRED = [line.strip() for line in open('requirements/base.txt').readlines()]

# The rest you shouldn't have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for that!

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.rst' is present in your MANIFEST.in file!
# with io.open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
#     long_description = '\n' + f.read()

try:
    #import pypandoc
    #long_description = pypandoc.convert_file("README.md", "rst")
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except ImportError:
    print('WARNING: description is empty, consider installing pypandoc: pip install --user pypandoc')
    long_description = ''

# Load the package's __version__.py module as a dictionary.
about = {}
with open(os.path.join(here, NAME, '__version__.py')) as f:
    exec(f.read(), about)


class UploadCommand(Command):
    """Support setup.py upload."""

    description = 'Build and publish the package.'
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status('Removing previous builds…')
            rmtree(os.path.join(here, 'dist'))
        except OSError:
            pass

        self.status('Building Source and Wheel (universal) distribution…')
        os.system('{0} setup.py sdist bdist_wheel --universal'.format(sys.executable))

        self.status('Uploading the package to PyPi via Twine…')
        os.system('twine upload dist/*')

        sys.exit()


packages = find_packages(
    # where='brotab',
    # exclude=('brotab.tests', 'firefox_extension', 'firefox_mediator')
    #exclude=('tests', 'firefox_extension', 'firefox_mediator')
    include=(
        'brotab',
        'brotab.tests',
        'brotab.search',
        'brotab.mediator',
        'brotab.albert',
    ),
    exclude=('firefox_extension', 'firefox_mediator')
)
print('>>', packages)


# Where the magic happens:
setup(
    name=NAME,
    version=about['__version__'],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    packages=packages,
    # packages=find_packages(
    #     where='brotab',
    #     # exclude=('brotab.tests', 'firefox_extension', 'firefox_mediator')
    #     exclude=('tests', 'firefox_extension', 'firefox_mediator')
    # ),
    data_files=[
        ('config', ['brotab/mediator/chromium_mediator.json',
                    'brotab/mediator/firefox_mediator.json']),
    ],
    # If your package is a single module, use this instead of 'packages':
    # py_modules=['mypackage'],

    entry_points={
        'console_scripts': [
            'brotab=brotab.main:main',
            'bt=brotab.main:main',
            'bt_mediator=brotab.mediator.brotab_mediator:main',
        ],
    },
    install_requires=REQUIRED,
    include_package_data=True,
    license='MIT',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython'
    ],
    # $ setup.py publish support.
    cmdclass={
        'upload': UploadCommand,
    },
)
