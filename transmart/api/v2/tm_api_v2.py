"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""

import logging
from urllib.parse import unquote_plus

import requests
from functools import wraps
from pandas.io.json import json_normalize

from .concept_search import ConceptSearcher
from .data_structures import ObservationSet, ObservationSetHD, TreeNodes, PatientSets, Studies, StudyList
from .query import Query, ObservationConstraint, Queryable, BiomarkerConstraint
from ..tm_api_base import TransmartAPIBase

logger = logging.getLogger('tm-api')


def default_constraint(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if kwargs.get('constraint') is None:
            if not any([isinstance(o, Queryable) for o in args]):
                kwargs['constraint'] = ObservationConstraint(**kwargs)
        return func(*args, **kwargs)
    return wrapper


class TransmartV2(TransmartAPIBase):
    """ Connect to tranSMART using Python. """

    def __init__(self, host, user=None, password=None, print_urls=False, interactive=True):
        """
        Create the python transmart client by providing user credentials.

        :param host: a transmart URL (e.g. http://transmart-test.thehyve.net)
        :param user: if not given, it asks for it.
        :param password: if not given, it asks for it.
        :param print_urls: print the url of handles being used.
        :param interactive: automatically build caches for interactive use.
        """
        super().__init__(host, user, password, print_urls)
        self.studies = None
        self.tree_dict = None
        self.search_tree_node = None
        self.interactive = interactive

        if interactive:
            self.build_cache()

    def build_cache(self):
        logger.debug('Caching list of studies.')
        self.get_studies()

        logger.debug('Caching full tree as tree_dict.')
        full_tree = self.tree_nodes()
        self.tree_dict = full_tree.tree_dict

        self.search_tree_node = ConceptSearcher(self.tree_dict, full_tree.identity).search

    def query(self, q):
        """ Perform query using API client using a Query object """

        url = "{}{}".format(self.host, q.handle)

        headers = q.headers
        headers['Authorization'] = 'Bearer ' + self.access_token

        if q.method.upper() == 'GET':
            r = requests.get(url, params=q.params, headers=headers)
        else:
            r = requests.post(url, json=q.json, params=q.params, headers=headers)

        if self.print_urls:
            print(unquote_plus(r.url))

        return r.json()

    @default_constraint
    def get_observations(self, constraint=None, as_dataframe=False, **kwargs):
        """
        Get observations, from the main table in the transmart data model.

        :param constraint: Constraint object. If left None, any keyword arguments
           are added to the constraint.
        :param as_dataframe: If True, convert json response to dataframe directly
        :return: dataframe or direct json
        """
        q = Query(handle='/v2/observations',
                  params=dict(
                      type='clinical',
                      constraint=str(constraint))
                  )

        observations = ObservationSet(self.query(q))

        if as_dataframe:
            return observations.dataframe

        return observations

    @default_constraint
    def get_patients(self, constraint=None, as_dataframe=False, **kwargs):
        """
        Get patients.

        :param constraint: Constraint object. If left None, any keyword arguments
           are added to the constraint.
        :param as_dataframe: If True, convert json response to dataframe directly
        :return: dataframe or direct json
        """
        q = Query(handle='/v2/patients', method='POST', json={'constraint': constraint.json()})

        patients = self.query(q)

        if as_dataframe:
            patients = json_normalize(patients['patients'])
        return patients

    def get_patient_sets(self, patient_set_id=None):
        q = Query(handle='/v2/patient_sets')

        if patient_set_id:
            q.handle += '/{}'.format(patient_set_id)

        return PatientSets(self.query(q))

    @default_constraint
    def create_patient_set(self, name, constraint=None, **kwargs):
        """
        Create a patient set that can be reused at a later stage.

        :param name: name of the patient set to create.
        :param constraint: observation constraints to use in query.
        :return: direct json
        """
        q = Query(handle='/v2/patient_sets',
                  method="POST",
                  params={"name": name},
                  json=constraint.json()
                  )

        return self.query(q)

    def get_studies(self, as_dataframe=False):
        """
        Get all studies.

        :param as_dataframe: If True, convert json response to dataframe
        :return: dataframe or Studies object
        """

        q = Query(handle='/v2/studies')

        studies = Studies(self.query(q))

        if self.studies is None:
            self.studies = StudyList(studies.dataframe.studyId)

        if as_dataframe:
            studies = studies.dataframe

        return studies

    def get_concepts(self, **kwargs):
        q = Query(handle='/v2/concepts')
        return json_normalize(self.query(q).get('concepts'))

    def tree_nodes(self, root=None, depth=0, counts=False, tags=True, hal=False):
        """
        Return the tree hierarchy

        :param root: Specify the root of the tree to be returned
        :param depth: The number of levels from the root need to be returned
        :param counts: Whether to include counts with the tree nodes
        :param tags: Whether to include metadata tags with the tree nodes
        :param hal: Whether to return Hal or not (JSON)
        :return:
        """

        q = Query(handle='/v2/tree_nodes',
                  params={'root': root,
                          'depth': depth,
                          'counts': counts,
                          'tags': tags},
                  hal=hal)

        tree_nodes = TreeNodes(self.query(q))

        return tree_nodes

    @default_constraint
    def get_hd_node_data(self, constraint=None, biomarker_constraint=None, biomarkers: list=None,
                         biomarker_type='genes', projection='all_data', **kwargs):
        """
        :param constraint:
        :param biomarker_constraint:
        :param biomarkers: list of markers to get.
        :param biomarker_type: ['genes', 'transcripts']
        :param projection: ['all_data', 'zscore', 'log_intensity']
        :return:
        """
        if biomarker_constraint is None:
            biomarker_constraint = BiomarkerConstraint(biomarkers=biomarkers,
                                                       biomarker_type=biomarker_type)

        q = Query(handle='/v2/observations',
                  method='GET',
                  params=dict(
                      type='autodetect',
                      projection=projection,
                      constraint=str(constraint),
                      biomarker_constraint=str(biomarker_constraint))
                  )

        return ObservationSetHD(self.query(q))

    @default_constraint
    def aggregates_per_concept(self, constraint=None, **kwargs):
        q = Query(handle='/v2/observations/aggregates_per_concept',
                  method='POST',
                  json={'constraint': constraint.json()}
                  )
        return self.query(q)

    @default_constraint
    def dimension_elements(self, constraint=None, dimension=None, **kwargs):
        q = Query(handle='/v2/dimensions/{}/elements'.format(dimension),
                  method='GET',
                  params=dict(
                      constraint=str(constraint))
                  )

        return self.query(q)

    def new_constraint(self, *args, **kwargs):
        return ObservationConstraint(api=self, *args, **kwargs)

    new_constraint.__doc__ = ObservationConstraint.__init__.__doc__
