#!/bin/bash

# Create __init__.py files
mkdir -p src/scrapers src/data_processing src/utils src/scripts
touch src/__init__.py
touch src/scrapers/__init__.py
touch src/data_processing/__init__.py
touch src/utils/__init__.py
touch src/scripts/__init__.py

# Create directory for data
mkdir -p data/scraped data/processed

# Create a setup.py file for the package
echo 'from setuptools import setup, find_packages

setup(
    name="zoningking",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "requests",
        "beautifulsoup4",
        "pandas",
        "googlesearch-python",
        "newspaper3k"
    ]
)' > setup.py