'''
* Copyright (c) 2015 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
* Author: Ruslan Forostianov

* Modified by Laura Madrid on 08/03/2017
* in order to make it compatible with transmart v16.2
'''

import json
import urllib.request
import urllib.parse
import urllib.error
from highdim_pb2 import HighDimHeader
from highdim_pb2 import Row
from google.protobuf import text_format
import google.protobuf.internal.decoder as decoder


class TransmartApi(object):

    def __init__(self, host, user, password, apiversion):
        self.host = host
        self.user = user
        self.password = password
        if apiversion in [1, 2]:
            self.apiversion = apiversion
        else:
            raise ValueError("Not a valid TranSMART API version")
        self.access_token = None

    def access(self):
        try:
            self._get_access_token()
            return 'SUCCESS'
        except urllib.error.HTTPError:
            return 'ERROR'

    def get_observations(self, study, hal=False):
        if self.apiversion == 1:
            url = '%s/studies/%s/observations' % (self.host, study)
        elif self.apiversion == 2:
            url = '%s/v2/observations?constraint={"type":"StudyNameConstraint","studyId":"%s"}'\
                % (self.host, study)
        observations = self._get_json(url, self._get_access_token(), hal=hal)
        return observations

    def get_concepts(self, study, hal=False):
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
        headers = {}
        headers['Accept'] = 'application/%s;charset=UTF-8' % ('hal+json' if hal else 'json')
        if access_token is not None:
            headers['Authorization'] = 'Bearer ' + access_token
        req2 = urllib.request.Request(url=url, data=b'', headers=headers)
        r2 = urllib.request.urlopen(req2)
        return json.loads(r2.read().decode('utf-8'))

    def _get_json(self, url, access_token=None, hal=False):
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
