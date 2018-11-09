"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""
# pylint: disable-msg=W0614,W0401,W0611,W0622

# flake8: noqa

from itertools import chain
import logging
logger = logging.getLogger('tm-api')

# Let users know if they're missing any of our hard dependencies
minimal = ("requests", "click")
backend = ("pandas", "google.protobuf", "arrow")
full = ("whoosh", "ipywidgets", "IPython", "bqplot")

missing_dependencies = set()

for dependency in chain(minimal, backend, full):
    try:
        __import__(dependency)
    except ImportError as e:
        missing_dependencies.add(dependency)

if missing_dependencies:
    msg = "Missing dependencies: {}".format(', '.join(missing_dependencies))
    logger.warning(msg)

_hard = missing_dependencies.intersection(minimal)

if _hard:
    raise ImportError('Missing required dependencies {}'.format(_hard))
elif missing_dependencies.intersection(backend):
    logger.warning('Running in minimal dependency mode. Only administrative calls are available.')
    dependency_mode = 'MINIMAL'
elif missing_dependencies.intersection(full):
    logger.warning('No Javascript dependencies found. Running in headless mode.')
    dependency_mode = 'BACKEND'
else:
    dependency_mode = 'FULL'

del (minimal, backend, full, _hard, missing_dependencies,
     chain, dependency, logging)

from .main import get_api


__version__ = "0.2.4"
__author__ = 'The Hyve'
