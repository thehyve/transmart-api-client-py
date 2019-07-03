"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""

import logging
from functools import wraps
from json import JSONDecodeError
from urllib.parse import unquote_plus

import requests

import transmart
from ..auth import get_auth

if transmart.dependency_mode == 'FULL':

    from .concept_search import ConceptSearcher
    from .constraints import ObservationConstraint, Queryable, BiomarkerConstraint

if transmart.dependency_mode in ('FULL', 'BACKEND'):
    from pandas.io.json import json_normalize
    from .data_structures import (ObservationSet, ObservationSetHD, TreeNodes, Patients,
                                  PatientSets, Studies, StudyList, RelationTypes)


logger = logging.getLogger('tm-api')


def default_constraint(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if kwargs.get('constraint') is None:
            if not any([isinstance(o, Queryable) for o in args]):
                kwargs['constraint'] = ObservationConstraint(**kwargs)
        return func(*args, **kwargs)
    return wrapper


def add_to_queryable(func):
    """
    This decorator allows registration a method to an ConstraintsObjects,
    so it can be accessed more easily.
    """
    func.__query_method__ = True
    return func


class Query:
    """ Utility to build queries for transmart v2 api. """

    def __init__(self, handle=None, method='GET', params=None, hal=False, json=None):
        self.handle = handle
        self.method = method
        self.hal = hal
        self.params = params
        self.json = json

    @property
    def headers(self):
        return {'Accept': 'application/{};charset=UTF-8'.format('hal+json' if self.hal else 'json')}


class TransmartV2:
    """ Connect to tranSMART v2 API using Python. """

    def __init__(self, host, offline_token=None, kc_url=None, kc_realm=None,
                 client_id=None, print_urls=False, interactive=True, verify=None):
        """
        Create the python transmart client by providing user credentials.

        :param host: a transmart URL (e.g. http://transmart-test.thehyve.net)
        :param offline_token: if not given, it asks for it.
        :param kc_url: KeyCloak hostname (e.g. https://keycloak-test.thehyve.net)
        :param kc_realm: Realm that is registered for the transmart api host to listen.
        :param print_urls: print the url of handles being used.
        :param interactive: automatically build caches for interactive use.
        :param client_id: client id in keycloak.
        :param verify: Either a boolean, in which case it controls whether we verify
        the server’s TLS certificate, or a string, in which case it must be a path
        to a CA bundle to use. Defaults to True.
        """
        self.studies = None
        self.tree_dict = None
        self.search_tree_node = None
        self.relation_types = None
        self.host = host
        self.interactive = interactive
        self.print_urls = print_urls
        self.verify = verify

        self.auth = get_auth(host, offline_token, kc_url, kc_realm, client_id)

        self._admin_call_factory('/v2/admin/system/after_data_loading_update')
        self._admin_call_factory('/v2/admin/system/config')
        self._admin_call_factory('/v2/admin/system/update_status')
        self._admin_call_factory('/v2/admin/system/clear_cache')

        self._observation_call_factory('aggregates_per_concept')
        self._observation_call_factory('counts')
        self._observation_call_factory('counts_per_concept')
        self._observation_call_factory('counts_per_study')
        self._observation_call_factory('counts_per_study_and_concept')

        if interactive and transmart.dependency_mode == 'FULL':
            self.build_cache()

    def build_cache(self):
        logger.debug('Caching list of studies.')
        self.get_studies()

        logger.debug('Caching full tree as tree_dict.')
        full_tree = self.tree_nodes()
        self.tree_dict = full_tree.tree_dict
        self.search_tree_node = ConceptSearcher(self.tree_dict, full_tree.identity).search

        logger.debug('Getting subject relationship types.')
        self.relation_types = RelationTypes(self.get_relation_types())

    def query(self, q):
        """ Perform query using API client using a Query object """

        url = "{}{}".format(self.host, q.handle)

        headers = q.headers
        headers['Authorization'] = 'Bearer ' + self.auth.access_token

        if q.method.upper() == 'GET':
            r = requests.get(url, params=q.params, headers=headers, verify=self.verify)
        else:
            r = requests.post(url, json=q.json, params=q.params, headers=headers, verify=self.verify)

        if self.print_urls:
            print(unquote_plus(r.url))

        return r.json()

    def admin(self):
        """
        Does nothing, but provide administrative functions via dot notation.
        """

    def _admin_call_factory(self, handle, doc=None):
        def func():
            q = Query(handle=handle, method='GET')
            try:
                return self.query(q)
            except JSONDecodeError:
                print('Not a valid JSON response. Returning None.')

        func.__doc__ = doc
        name = handle.split('/')[-1]  # pick last part of handle as name.
        self.admin.__dict__[name] = func

    @default_constraint
    @add_to_queryable
    def observations(self, constraint=None, as_dataframe=False, **kwargs):
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

    def _observation_call_factory(self, handle, doc=None):

        def func(constraint=None, *args, **kwargs):
            q = Query(handle='/v2/observations/' + handle,
                      method='POST',
                      json={'constraint': constraint.json()}
                      )
            return self.query(q)

        func.__doc__ = doc
        self.observations.__dict__[handle] = add_to_queryable(default_constraint(func))

    @default_constraint
    @add_to_queryable
    def patients(self, constraint=None, **kwargs):
        """
        Get patients.

        :param constraint: Constraint object. If left None, any keyword arguments
           are added to the constraint.
        :return: dataframe or direct json
        """
        q = Query(handle='/v2/patients', method='POST', json={'constraint': constraint.json()})
        return Patients(self.query(q))

    def patient_sets(self, patient_set_id=None):
        q = Query(handle='/v2/patient_sets')

        if patient_set_id:
            q.handle += '/{}'.format(patient_set_id)

        return PatientSets(self.query(q))

    @default_constraint
    @add_to_queryable
    def create_patient_set(self, name: str, constraint=None, **kwargs):
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

    def get_studies(self, as_json=False):
        """
        Get all studies.

        :param as_json: If True, return direct json response.
        :return: json or Studies object
        """

        q = Query(handle='/v2/studies')

        json_ = self.query(q)

        if as_json or transmart.dependency_mode == 'MINIMAL':
            return json_

        studies = Studies(json_)

        if self.studies is None:
            self.studies = StudyList(studies.dataframe.studyId)

        return studies

    def concepts(self, **kwargs):
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
    @add_to_queryable
    def get_hd_node_data(self, constraint=None, biomarker_constraint=None, biomarkers: list = None,
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
    @add_to_queryable
    def dimension_elements(self, dimension, constraint=None, **kwargs):
        q = Query(handle='/v2/dimensions/{}/elements'.format(dimension),
                  method='GET',
                  params=dict(
                      constraint=str(constraint))
                  )

        return self.query(q)

    def get_relation_types(self):
        q = Query(handle='/v2/pedigree/relation_types')
        return self.query(q)

    def supported_fields(self):
        q = Query(handle='/v2/supported_fields')
        return self.query(q)

    def new_constraint(self, *args, **kwargs):
        return ObservationConstraint(api=self, *args, **kwargs)

    try:
        new_constraint.__doc__ = ObservationConstraint.__init__.__doc__
    except NameError:
        pass
