"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
* Original Author: Ruslan Forostianov

* Contributors:
    - Jochem Bijlard
    - Laura Madrid
    - Ward Weistra

* Modified by Laura Madrid on 08/03/2017
* in order to make it compatible with transmart v16.2
"""
import transmart
if transmart.dependency_mode == 'FULL':
    import requests

    import google.protobuf.internal.decoder as decoder
    from pandas.io.json import json_normalize

    from .highdim_pb2 import HighDimHeader
    from .highdim_pb2 import Row
    import urllib

    from ..auth import get_auth


class TransmartV1:
    """ Connect to tranSMART V1 api using Python. """

    def __init__(self, host, offline_token=None, kc_url=None,
                 kc_realm=None, client_id=None, print_urls=False, verify=None, *args, **kwargs):
        """
        Create the python transmart client by providing user credentials.

        :param host: a transmart URL (e.g. http://transmart-test.thehyve.net)
        :param offline_token: if not given, it asks for it.
        :param kc_url: KeyCloak hostname (e.g. https://keycloak-test.thehyve.net).
        :param kc_realm: Realm that is registered for the transmart api host to listen.
        :param client_id: client id in keycloak.
        :param print_urls: print the url of handles being used.
        :param verify: Either a boolean, in which case it controls whether we verify
        the server’s TLS certificate, or a string, in which case it must be a path
        to a CA bundle to use. Defaults to True.
        """
        self.host = host
        self.print_urls = print_urls
        self.verify = verify
        self.auth = get_auth(host, offline_token, kc_url, kc_realm, client_id)

    def get_observations(self, study=None, patientSet=None, as_dataframe=True, hal=False):
        """
        Get observations, from the main table in the transmart data model.

        :param study: studyID
        :param patientSet: patient set id
        :param as_dataframe: If True (default), convert json response to dataframe
        :param hal: ?
        :return: dataframe or direct json
        """
        url = '%s/studies/%s/observations' % (self.host, study)

        observations = self._get_json(url, hal=hal)

        if as_dataframe:
            observations = json_normalize(observations)

        return observations

    def get_patients(self, study=None, patientSet=None, as_dataframe=True, hal=False):
        """
        Get patients.

        :param study: studyID
        :param patientSet: patient set id
        :param as_dataframe: If True (default), convert json response to dataframe
        :param hal: ?
        :return: dataframe or direct json
        """
        raise ValueError("Function not implemented in Python client for API V1")

    def get_studies(self, as_dataframe=True, hal=False):
        """
        Get all studies.

        :param as_dataframe: If True (default), convert json response to dataframe
        :param hal: ?
        :return: dataframe or direct json
        """
        url = '%s/studies' % (self.host)

        studies = self._get_json(url, hal=hal)

        if as_dataframe:
            studies = json_normalize(studies['studies'])

        return studies

    def get_concepts(self, study, hal=False):
        url = '%s/studies/%s/concepts/' % (self.host, study)
        return self._get_json(url, hal=hal)

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
        concepts = self.get_concepts(study, hal=True)
        found_condepts_hrefs = []
        for t in concepts['_embedded']['ontology_terms']:
            if t['type'] == 'HIGH_DIMENSIONAL' and t['name'] == node_name:
                found_condepts_hrefs.append(t['_links']['self']['href'])
        hd_node_url = '%s%s/highdim' % (self.host, found_condepts_hrefs[0])
        hd_node_meta = self._get_json(hd_node_url)
        hd_data_type_name = hd_node_meta['dataTypes'][0]['name']
        hd_node_data_url = '%s?projection=%s&dataType=%s' % (
            hd_node_url, projection, hd_data_type_name)
        if genes is not None:
            hd_node_data_url = hd_node_data_url + \
                '&' + urllib.parse.urlencode({'dataConstraints': {'genes': [{'names': genes}]}})
        hd_data = self._get_protobuf(hd_node_data_url)
        return hd_data

    def _get_json_post(self, url, hal=False):

        if self.print_urls:
            print(url)

        headers = {}
        headers['Accept'] = 'application/%s;charset=UTF-8' % ('hal+json' if hal else 'json')
        if self.auth.access_token is not None:
            headers['Authorization'] = 'Bearer ' + self.auth.access_token
        r = requests.post(url, headers=headers, verify=self.verify)
        r.raise_for_status()
        return r.json()

    def _get_json(self, url, hal=False):

        if self.print_urls:
            print(url)

        headers = {
            'Accept': 'application/%s;charset=UTF-8' % ('hal+json' if hal else 'json')
        }
        if self.auth.access_token is not None:
            headers['Authorization'] = 'Bearer ' + self.auth.access_token

        r = requests.get(url, headers=headers, verify=self.verify)
        r.raise_for_status()
        return r.json()

    def _parse_protobuf(self, data):
        hdHeader = HighDimHeader()
        (length, start) = decoder._DecodeVarint(data, 0)
        hdHeader.ParseFromString(data[start:start+length])
        data = data[start+length:]
        hdRows = []
        n = len(data)
        start = 0
        while start < n:
            (length, start) = decoder._DecodeVarint(data, start)
            hdRow = Row()
            hdRow.ParseFromString(data[start:start+length])
            hdRows.append(hdRow)
            start += length
        return (hdHeader, hdRows)

    def _get_protobuf(self, url):
        headers = {
            'Accept': 'application/octet-stream'
        }
        if self.auth.access_token is not None:
            headers['Authorization'] = 'Bearer ' + self.auth.access_token
        req = urllib.request.Request(url, headers=headers)
        return self._parse_protobuf(urllib.request.urlopen(req).read())


