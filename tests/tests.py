#!/usr/bin/env python3

import unittest
from unittest import mock

from transmart import get_api
from transmart.api.v1.tm_api_v1 import TransmartV1
from transmart.api.v2.tm_api_v2 import TransmartV2

import test_values

class PythonClientTestCase(unittest.TestCase):

    @mock.patch('transmart.api.tm_api_base.TransmartAPIBase._get_access_token')
    def test_get_api(self, mock_get_access_token):
        host = 'https://transmart.thehyve.net'
        user = 'demo-user'
        password = 'demo-user'
        mock_get_access_token.return_value = test_values.response_request_access_token

        api = get_api(host=host, user=user, password=password)
        assert isinstance(api, TransmartV2)
    
if __name__ == '__main__':
    unittest.main()
