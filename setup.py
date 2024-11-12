from setuptools import setup, find_packages

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
)
