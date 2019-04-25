#!/usr/bin/env python3
"""Open Peer Power setup script."""
from datetime import datetime as dt
from setuptools import setup, find_packages

import openpeerpower.const as opp_const

PROJECT_NAME = 'Open Peer Power'
PROJECT_PACKAGE_NAME = 'openpeerpower'
PROJECT_LICENSE = 'Apache License 2.0'
PROJECT_AUTHOR = 'Paul Caston'
PROJECT_COPYRIGHT = ' 2018-{}, {}'.format(dt.now().year, PROJECT_AUTHOR)
PROJECT_URL = 'https://OpenPeerPower.io/'
PROJECT_EMAIL = 'paul@caston.id.au'

PROJECT_GITHUB_USERNAME = 'open-peer-power'
PROJECT_GITHUB_REPOSITORY = 'open-peer-power'

PYPI_URL = 'https://pypi.python.org/pypi/{}'.format(PROJECT_PACKAGE_NAME)
GITHUB_PATH = '{}/{}'.format(
    PROJECT_GITHUB_USERNAME, PROJECT_GITHUB_REPOSITORY)
GITHUB_URL = 'https://github.com/{}'.format(GITHUB_PATH)

DOWNLOAD_URL = '{}/archive/{}.zip'.format(GITHUB_URL, opp_const.__version__)
PROJECT_URLS = {
}

PACKAGES = find_packages(exclude=['tests', 'tests.*'])

REQUIRES = [
    'async_timeout==3.0.1',
]

MIN_PY_VERSION = '.'.join(map(str, opp_const.REQUIRED_PYTHON_VER))

setup(
    name=PROJECT_PACKAGE_NAME,
    version=opp_const.__version__,
    url=PROJECT_URL,
    download_url=DOWNLOAD_URL,
    project_urls=PROJECT_URLS,
    author=PROJECT_AUTHOR,
    author_email=PROJECT_EMAIL,
    packages=PACKAGES,
    include_package_data=True,
    zip_safe=False,
    install_requires=REQUIRES,
    python_requires='>={}'.format(MIN_PY_VERSION),
    test_suite='tests',
    entry_points={
        'console_scripts': [
            'opp = openpeerpower.__main__:main'
        ]
    },
)
