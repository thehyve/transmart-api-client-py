"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""

import requests

from pandas.io.json import json_normalize

from ..tm_api_base import TransmartAPIBase
from .query import Query
from .data_structures import ObservationSet


class TransmartV2(TransmartAPIBase):
    """ Connect to tranSMART using Python. """

    def __init__(self, host, user=None, password=None, print_urls=False):
        """
        Create the python transmart client by providing user credentials.

        :param host: a transmart URL (e.g. http://transmart-test.thehyve.net)
        :param user: if not given, it asks for it.
        :param password: if not given, it asks for it.
        :param print_urls: print the url of handles being used.
        """
        super().__init__(host, user, password, print_urls)

    def get_observations(self, study=None, patient_set=None, as_dataframe=True, hal=False):
        """
        Get observations, from the main table in the transmart data model.

        :param study: studyID
        :param patient_set: patient set id
        :param as_dataframe: If True (default), convert json response to dataframe
        :param hal: ?
        :return: dataframe or direct json
        """

        q = Query(handle='/v2/observations',
                  params={'type': 'clinical'},
                  in_study=study,
                  in_patientset=patient_set,
                  hal=hal)

        observations = ObservationSet(self.query(q))

        if as_dataframe:
            return observations.dataframe

        return observations

    def get_patients(self, study=None, patient_set=None, as_dataframe=True, hal=False):
        """
        Get patients.

        :param study: studyID
        :param patient_set: patient set id
        :param as_dataframe: If True (default), convert json response to dataframe
        :param hal: ?
        :return: dataframe or direct json
        """
        q = Query(handle='/v2/patients', in_study=study, in_patientset=patient_set, hal=hal)

        patients = self.query(q)

        if as_dataframe:
            patients = json_normalize(patients['patients'])
        return patients

    def get_studies(self, as_dataframe=True, hal=False):
        """
        Get all studies.

        :param as_dataframe: If True (default), convert json response to dataframe
        :param hal: ?
        :return: dataframe or direct json
        """

        q = Query(handle='/v2/studies', hal=hal)

        studies = self.query(q)

        if as_dataframe:
            studies = json_normalize(studies['studies'])

        return studies

    def get_concepts(self, study, hal=False):
        raise NotImplementedError("Call not available for API V2.")

    def get_hd_node_data(self, study, node_name, projection='all_data', genes=None):
        """
        Parameters
        ----------
        node_name: string
           Name of the leaf node
        projection : string
           Possible values: default_real_projection, zscore, log_intensity, all_data (default)
        genes: list of strings
            Gene names. e.g. 'TP53', 'AURCA'
        """
        raise NotImplementedError("Function not yet implemented in Python client for API V2")
        # TODO Create V2 version for highdimensional data

    def query(self, q):
        """ Perform query using API client """

        url = "{}{}".format(self.host, q.handle)
        if self.print_urls:
            print(q)

        headers = q.headers
        headers['Authorization'] = 'Bearer ' + self.access_token

        r = getattr(requests, q.method.lower())(url, params=q.params, headers=headers)
        return r.json()
