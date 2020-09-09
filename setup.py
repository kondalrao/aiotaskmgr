#!/usr/bin/env python3
import os

from setuptools import setup, find_packages


base_dir = os.path.dirname(__file__)

about = {}
with open(os.path.join(base_dir, "aiotaskmgr", "__about__.py")) as f:
    exec(f.read(), about)

setup(
    name=about["__title__"],
    version=about["__version__"],

    description=about["__summary__"],
    long_description=open('README.md').read(),
    license=about["__license__"],
    url=about["__uri__"],

    author=about["__author__"],
    author_email=about["__email__"],

    install_requires=['aiomonitor', 'eliot'],
    packages=find_packages(exclude=['tests']),

    classifiers=[
        "Intended Audience :: Developers",

        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
    ]
)
