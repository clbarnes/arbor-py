#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""
from typing import Dict, List
from setuptools import setup, find_packages
import itertools
from pathlib import Path
from runpy import run_path

root_dir = Path(__file__).resolve().parent

with open(root_dir / "README.rst") as readme_file:
    readme = readme_file.read()

with open(root_dir / "HISTORY.rst") as history_file:
    history = history_file.read()

version = run_path(str(root_dir / "arbor" / "version.py"))["__version__"]

requirements = ["numpy", "scipy"]

test_requirements = ["pytest"]

extras_require: Dict[str, List[str]] = {}
extras_require["all"] = list(itertools.chain.from_iterable(extras_require.values()))

setup(
    author="Chris L. Barnes",
    author_email="chrislloydbarnes@gmail.com",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Arbor.js in python, again",
    install_requires=requirements,
    extras_require=extras_require,
    license="GNU General Public License v3",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="arbor",
    name="arbor",
    packages=find_packages(include=["arbor"]),
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/clbarnes/arbor-py",
    version=version,
    zip_safe=False,
)
