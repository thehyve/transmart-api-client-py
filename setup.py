import setuptools
import os
import re


VERSIONFILE=os.path.join('transmart', '__init__.py')
verstrline = open(VERSIONFILE, "rt").read()
VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(VSRE, verstrline, re.M)
if mo:
    version_string = mo.group(1)
else:
    raise RuntimeError("Unable to find version string in {}.".format(VERSIONFILE,))

with open("requirements.txt", 'r') as f:
    required_packages = f.read().splitlines()

if os.environ.get('READTHEDOCS') == 'True':
    for dependency in ['pandas']:
        for package in required_packages:
            if package.startswith(dependency):
                required_packages.remove(package)

minimal = ["requests", "click"]
backend = ["pandas", "arrow"]

setuptools.setup(
    name="transmart",
    version=version_string,
    url="https://www.github.com/thehyve/transmart-api-client-py/",

    maintainer="developers@thehyve.nl",
    maintainer_email="developers@thehyve.nl",

    description="An python client for communicating with the transmart rest api.",

    packages=setuptools.find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,

    keywords=['transmart', 'rest', 'api', 'data', 'science'],

    download_url='https://github.com/thehyve/transmart-api-client-py/tarball/{}/'.format(version_string),

    install_requires=minimal,

    extras_require={
        "backend": backend,
        "full": required_packages},
    entry_points={
        'console_scripts': [
            'transmart-keycloak = transmart.api.utils.keycloak_role_manager:_role_manager_entry_point'
        ]
    },

    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
