"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""
import requests
import getpass

CLIENT_ID = 'glowingbear-js'


class TransmartAPIBase:
    """ Connect to tranSMART using Python. """

    def __init__(self, host, user=None, password=None, print_urls=False):

        self.host = host
        self.user = user or input("Username: ")
        self.print_urls = print_urls

        self.access_token = self._get_access_token(password)

    def _get_access_token(self, password):
        r = requests.post("{}/oauth/token".format(self.host),
                          params={'grant_type': 'password',
                                  'client_id': CLIENT_ID,
                                  'username': self.user,
                                  'password': password or getpass.getpass("Password: ")
                                  })
        r.raise_for_status()

        return r.json().get('access_token')

    def get_observations(self, study=None, patientSet=None, as_dataframe=True):
        raise NotImplementedError

    def get_patients(self, study=None, patientSet=None, as_dataframe=True):
        raise NotImplementedError

    def get_studies(self, as_dataframe=True):
        raise NotImplementedError

    def get_concepts(self, study):
        raise NotImplementedError

    def get_hd_node_data(self, study, node_name, projection='all_data', genes=None):
        raise NotImplementedError
