"""
This module provides functions to work with google calendar services
"""

from setuptools import find_packages, setup

setup(
    name="gcaltool",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "google-auth",
        "google-auth-httplib2",
        "google-api-python-client",
        "httplib2",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "gcaltool=gcaltool.cli:main",
        ],
    },
    include_package_data=True,
    description="A tool for managing Google Calendar through the CLI",
    author="aringo",
    author_email="aringo@blacklabsec.com",
    url="https://github.com/",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
