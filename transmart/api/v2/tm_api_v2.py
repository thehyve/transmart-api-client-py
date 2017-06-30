"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""

import requests

from pandas.io.json import json_normalize

from ..tm_api_base import TransmartAPIBase
from .query import Query
from .data_structures import ObservationSet, ObservationSetHD, TreeNodes, PatientSets, Studies, StudyList


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
        self.studies = None

    def query(self, q):
        """ Perform query using API client using a Query object """

        url = "{}{}".format(self.host, q.handle)
        if self.print_urls:
            print(q)

        headers = q.headers
        headers['Authorization'] = 'Bearer ' + self.access_token

        if q.method.upper() == 'GET':
            r = requests.get(url, params=q.params, headers=headers)
        else:
            r = requests.post(url, json=q.params, headers=headers)

        return r.json()

    def get_observations(self, study=None, patient_set=None, as_dataframe=False):
        """
        Get observations, from the main table in the transmart data model.

        :param study: studyID
        :param patient_set: patient set id
        :param as_dataframe: If True, convert json response to dataframe directly
        :return: dataframe or ObservationSet object
        """

        q = Query(handle='/v2/observations',
                  params={'type': 'clinical'},
                  in_study=study,
                  in_patientset=patient_set)

        observations = ObservationSet(self.query(q))

        if as_dataframe:
            return observations.dataframe

        return observations

    def get_patients(self, study=None, patient_set=None, as_dataframe=False):
        """
        Get patients.

        :param study: studyID
        :param patient_set: patient set id
        :param as_dataframe: If True, convert json response to dataframe directly
        :return: dataframe or direct json
        """
        q = Query(handle='/v2/patients', in_study=study, in_patientset=patient_set)

        patients = self.query(q)

        if as_dataframe:
            patients = json_normalize(patients['patients'])
        return patients

    def get_studies(self, as_dataframe=False):
        """
        Get all studies.

        :param as_dataframe: If True, convert json response to dataframe
        :return: dataframe or Studies object
        """

        q = Query(handle='/v2/studies')

        studies = Studies(self.query(q))

        self.studies = StudyList(studies.dataframe.studyId)

        if as_dataframe:
            studies = studies.dataframe

        return studies

    def get_concepts(self, study, hal=False):
        raise NotImplementedError("Call not available for API V2.")

    def tree_nodes(self, root=None, depth=0, counts=True, tags=True, hal=False):
        """

        :param root:
        :param depth:
        :param counts:
        :param tags:
        :param hal:
        :return:
        """
        q = Query(handle='/v2/tree_nodes',
                  params={'root': root,
                          'depth': depth,
                          'counts': counts,
                          'tags': tags},
                  hal=hal)

        return TreeNodes(self.query(q))

    def get_patient_sets(self):
        q = Query(handle='/v2/patient_sets')
        return PatientSets(self.query(q))

    def get_hd_node_data(self, study, hd_type='autodetect', genes=None, transcripts=None, concept=None,
                         patient_set=None, projection='all_data'):
        """

        :param study:
        :param hd_type:
        :param genes:
        :param transcripts:
        :param concept:
        :param patient_set:
        :param projection: ['all_data', 'zscore', 'log_intensity']
        :return:
        """
        q = Query(handle='/v2/observations',
                  method='POST',
                  params={'type': hd_type,
                          'projection': projection},
                  in_study=study,
                  in_patientset=patient_set,
                  in_concept=concept,
                  in_gene_list=genes,
                  in_transcript_list=transcripts
                  )
        return ObservationSetHD(self.query(q))
