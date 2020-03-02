from setuptools import setup, find_packages

setup(
    name="ecmwf-api-futures",
    description="A future-based interface to ecmwf-api-client",
    version="1.1.1",
    author="Christopher Polster",
    url="https://github.com/chpolste/ecmwf-api-futures",
    packages=find_packages(),
    install_requires=[
        "ecmwf-api-client"
    ]
)

