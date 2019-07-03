# Python client for retrieving data from tranSMART

[![Build Status](https://travis-ci.org/thehyve/transmart-api-client-py.svg?branch=master)](https://travis-ci.org/thehyve/transmart-api-client-py)
[![codecov](https://codecov.io/gh/thehyve/transmart-api-client-py/branch/master/graph/badge.svg)](https://codecov.io/gh/thehyve/transmart-api-client-py)
[![Binder](https://mybinder.org/badge.svg)](https://mybinder.org/v2/gh/thehyve/transmart-api-client-py/master?urlpath=/lab/tree/examples/Example.ipynb)

This is meant to work with Python 3.x only.

## Installation

`pip3 install transmart` for minimal dependencies, but only administrative calls are available.

`pip3 install transmart[full]` for the full thing.


## Demo

[Launch the live demo notebook using Binder](https://mybinder.org/v2/gh/thehyve/transmart-api-client-py/master?urlpath=/lab/tree/examples/Example.ipynb)


## Usage

### Main client
See the notebook in `./examples` or go live via the binder link above. 


### Entry points
After installing via pip there should be a CLI tool available to add necessary roles to KeyCloak.

```bash
$ transmart-keycloak --help
Usage: transmart-keycloak [OPTIONS]

Options:
  -t, --transmart TEXT      tranSMART host url, e.g. https://transmart-
                            dev.thehyve.net.  [required]
  -k, --kc-url TEXT         KeyCloak host, e.g. https://keycloak-dwh-
                            test.thehyve.net.  [required]
  -r, --realm TEXT          KeyCloak realm.  [required]
  -o, --offline-token TEXT  KeyCloak offline token, will be asked for if not provided.
  -s, --study TEXT          Add roles for this study IDs. If not provided, add all
                            studies.
  --version                 Show the version and exit.
  --help                    Show this message and exit.
```