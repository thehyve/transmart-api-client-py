'''
* Copyright (c) 2015 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
* Author: Ruslan Forostianov
'''

import json
import urllib
import urllib2
from highdim_pb2 import HighDimHeader
from highdim_pb2 import Row
from google.protobuf import text_format
import google.protobuf.internal.decoder as decoder
#change from guest
class TransmartApi(object):
    
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
        self.access_token = None

    def access(self):
        try:
            self._get_access_token()
            return 'SUCCESS'
        except urllib2.HTTPError:
            return 'ERROR'
    
    def get_observations(self, study, hal = False):
        url = '%s/transmart/studies/%s/observations' % (self.host, study)
        observations = self._get_json(url, self._get_access_token(), hal = hal)
        return observations

    def get_concepts(self, study, hal = False):
        url = '%s/transmart/studies/%s/concepts/' % (self.host, study)
        return self._get_json(url, self._get_access_token(), hal = hal)
        
    def get_hd_node_data(self, study, node_name, projection='all_data', genes = None):
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
        concepts = self.get_concepts(study, hal = True)
        found_condepts_hrefs = [t['_links']['self']['href'] for t in concepts['_embedded']['ontology_terms'] if t['type'] == 'HIGH_DIMENSIONAL' and t['name'] == node_name]
        hd_node_url = '%s/transmart%s/highdim' % (self.host, found_condepts_hrefs[0])
        hd_node_meta = self._get_json(hd_node_url, self._get_access_token())
        hd_data_type_name = hd_node_meta['dataTypes'][0]['name']
        hd_node_data_url = '%s?projection=%s&dataType=%s' % (hd_node_url, projection, hd_data_type_name)
        if genes is not None:
            hd_node_data_url = hd_node_data_url + \
                '&' + urllib.urlencode({'dataConstraints': {'genes': [{'names': genes}]}})
        hd_data = self._get_protobuf(hd_node_data_url, self._get_access_token())
        return hd_data
    
    def _get_json(self, url, access_token = None, hal = False):
        headers = {}
        headers['Accept'] = 'application/%s;charset=UTF-8' % ('hal+json' if hal else 'json')
        if access_token is not None:
            headers['Authorization'] = 'Bearer ' + access_token
        req = urllib2.Request(url, headers = headers)
        res = urllib2.urlopen(req)
        return json.loads(res.read())
    
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
        
    def _get_protobuf(self, url, access_token = None):
        headers = {
            'Accept': 'application/octet-stream'
        }
        if access_token is not None:
            headers['Authorization'] = 'Bearer ' + access_token
        req = urllib2.Request(url, headers = headers)
        return self._parse_protobuf(urllib2.urlopen(req).read())
        
    def _get_access_token(self):
        if self.access_token is None:
            url = '%s/transmart/oauth/token' \
                  '?grant_type=password&client_id=glowingbear-js&client_secret=' \
                   '&username=%s&password=%s' % (self.host, self.user, self.password)
            access_token_dic = self._get_json(url)
            self.access_token = access_token_dic['access_token']
        return self.access_token