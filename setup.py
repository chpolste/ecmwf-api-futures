from setuptools import setup, find_packages

setup(
    name="ecmwfapi_futures",
    description="A future-based interface to ecmwf-api-client",
    version="1.0.0",
    author="Christopher Polster",
    url="https://github.com/chpolste/ecmwf-api-futures",
    packages=find_packages(),
    install_requires=[
        "ecmwf-api-client"
    ]
)

