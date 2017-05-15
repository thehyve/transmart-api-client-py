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

import json
import urllib.error
import urllib.parse
import urllib.request
import getpass

import google.protobuf.internal.decoder as decoder
from pandas.io.json import json_normalize

from transmart.highdim_pb2 import HighDimHeader
from transmart.highdim_pb2 import Row


class TransmartApi(object):
    """ Connect to tranSMART using Python. """

    def __init__(self, host, user=None, password=None, api_version=2, print_urls=False):
        """
        Create the python transmart client by providing user credentials.

        :param host: a transmart URL (e.g. http://transmart-test.thehyve.net)
        :param user: if not given, it asks for it.
        :param password: if not given, it asks for it.
        :param api_version: either 1 or 2. Default is 2.
        :param print_urls: print the url of handles being used.
        """
        api_versions = (1, 2)

        self.host = host
        self.user = user or input("Username: ")
        self.password = password or getpass.getpass("Password: ")
        self.print_urls = print_urls

        if api_version in api_versions:
            self._is_v2 = api_version == 2
        else:
            raise ValueError("Not a valid TranSMART API version. Choose from: "+str(api_versions))

        self.access_token = None

    def access(self):
        try:
            self._get_access_token()
            return 'Connected successfully'
        except urllib.error.HTTPError as error:
            return "ERROR: " + format(error)

    def get_observations(self, study=None, patientSet=None, as_dataframe=True, hal=False):
        """
        Get observations, from the main table in the transmart data model.

        :param study: studyID
        :param patientSet: patient set id
        :param as_dataframe: If True (default), convert json response to dataframe
        :param hal: ?
        :return: dataframe or direct json
        """
        if self._is_v2:
            url = ('%s/v2/observations') % (self.host)
            url += '?type=clinical'
            constraint = self._build_constraint(study=study, patientSet=patientSet)
            if constraint:
                url += '&'+constraint
        else:
            url = '%s/studies/%s/observations' % (self.host, study)

        observations = self._get_json(url, self._get_access_token(), hal=hal)

        if as_dataframe:
            if self._is_v2:
                observations = self._format_observations(observations)

            observations = json_normalize(observations)

        return observations

    @staticmethod
    def _format_observations(observations_result):
        output_cells = []
        indexed_dimensions = []
        inline_dimensions = []

        for dimension in observations_result['dimensionDeclarations']:
            if 'inline' in dimension:
                inline_dimensions.append(dimension)
            else:
                indexed_dimensions.append(dimension)

        for dimension in indexed_dimensions:
            dimension['values'] = observations_result['dimensionElements'][dimension['name']]

        for cell in observations_result['cells']:
            output_cell = {}

            i = 0
            for index in cell['dimensionIndexes']:
                if index is not None:
                    output_cell[indexed_dimensions[i]['name']] = \
                        indexed_dimensions[i]['values'][int(index)]
                i += 1

            i = 0
            for index in cell['inlineDimensions']:
                output_cell[inline_dimensions[i]['name']] = index
                i += 1

            if 'stringValue' in cell:
                output_cell['stringValue'] = cell['stringValue']
            if 'numericValue' in cell:
                output_cell['numericValue'] = cell['numericValue']
            output_cells.append(output_cell)
        return output_cells

    def get_patients(self, study=None, patientSet=None, as_dataframe=True, hal=False):
        """
        Get patients.

        :param study: studyID
        :param patientSet: patient set id
        :param as_dataframe: If True (default), convert json response to dataframe
        :param hal: ?
        :return: dataframe or direct json
        """
        if self._is_v2:
            url = ('%s/v2/patients') % (self.host)
            constraint = self._build_constraint(study=study, patientSet=patientSet)
            if constraint:
                url += '?'+constraint
        else:
            raise ValueError("Function not implemented in Python client for API V1")

        patients = self._get_json(url, self._get_access_token(), hal=hal)
        if as_dataframe:
            patients = json_normalize(patients['patients'])
        return patients

    def _build_constraint(self, study=None, patientSet=None):
        constraint = ''

        if study:
            constraint += '{"type":"study_name","studyId":"%s"}' % (study)
        if patientSet:
            constraint += '{"type":"patient_set","patientSetId":%s}' % (patientSet)

        if constraint != '':
            return 'constraint='+constraint
        else:
            return None

    def get_studies(self, as_dataframe=True, hal=False):
        """
        Get all studies.

        :param as_dataframe: If True (default), convert json response to dataframe
        :param hal: ?
        :return: dataframe or direct json
        """
        if self._is_v2:
            url = ('%s/v2/studies') % (self.host)
        else:
            url = '%s/studies' % (self.host)

        studies = self._get_json(url, self._get_access_token(), hal=hal)

        if as_dataframe:
            studies = json_normalize(studies['studies'])

        return studies

    def get_concepts(self, study, hal=False):
        if self._is_v2:
            raise NotImplementedError("Call not available for API V2")
        else:
            url = '%s/studies/%s/concepts/' % (self.host, study)
        return self._get_json(url, self._get_access_token(), hal=hal)

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
        if self._is_v2:
            raise NotImplementedError("Function not yet implemented in Python client for API V2")
            # TODO Create V2 version for highdimensional data

        concepts = self.get_concepts(study, hal=True)
        found_condepts_hrefs = []
        for t in concepts['_embedded']['ontology_terms']:
            if t['type'] == 'HIGH_DIMENSIONAL' and t['name'] == node_name:
                found_condepts_hrefs.append(t['_links']['self']['href'])
        hd_node_url = '%s%s/highdim' % (self.host, found_condepts_hrefs[0])
        hd_node_meta = self._get_json(hd_node_url, self._get_access_token())
        hd_data_type_name = hd_node_meta['dataTypes'][0]['name']
        hd_node_data_url = '%s?projection=%s&dataType=%s' % (
            hd_node_url, projection, hd_data_type_name)
        if genes is not None:
            hd_node_data_url = hd_node_data_url + \
                '&' + urllib.parse.urlencode({'dataConstraints': {'genes': [{'names': genes}]}})
        hd_data = self._get_protobuf(hd_node_data_url, self._get_access_token())
        return hd_data

    def _get_json_post(self, url, access_token=None, hal=False):

        if self.print_urls:
            print(url)

        headers = {}
        headers['Accept'] = 'application/%s;charset=UTF-8' % ('hal+json' if hal else 'json')
        if access_token is not None:
            headers['Authorization'] = 'Bearer ' + access_token
        req2 = urllib.request.Request(url=url, data=b'', headers=headers)
        r2 = urllib.request.urlopen(req2)
        return json.loads(r2.read().decode('utf-8'))

    def _get_json(self, url, access_token=None, hal=False):

        if self.print_urls:
            print(url)

        headers = {}
        headers['Accept'] = 'application/%s;charset=UTF-8' % ('hal+json' if hal else 'json')
        if access_token is not None:
            headers['Authorization'] = 'Bearer ' + access_token
        req = urllib.request.Request(url, headers=headers)
        res = urllib.request.urlopen(req)
        return json.loads(res.read().decode('utf-8'))

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

    def _get_protobuf(self, url, access_token=None):
        headers = {
            'Accept': 'application/octet-stream'
        }
        if access_token is not None:
            headers['Authorization'] = 'Bearer ' + access_token
        req = urllib.request.Request(url, headers=headers)
        return self._parse_protobuf(urllib.request.urlopen(req).read())

    def _get_access_token(self):
        if self.access_token is None:
            url = '%s/oauth/token' \
                  '?grant_type=password&client_id=glowingbear-js&client_secret=' \
                   '&username=%s&password=%s' % (self.host, self.user, self.password)
            access_token_dic = self._get_json_post(url)
            self.access_token = access_token_dic['access_token']
        return self.access_token
