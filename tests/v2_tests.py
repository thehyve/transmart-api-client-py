#!/usr/bin/env python3

import unittest
from transmart.api.v2.tm_api_v2 import TransmartV2

from tests.mock_server import TestMockServer, retry


class V2TestCase(TestMockServer):

    @retry
    def test_get_api(self):
        assert isinstance(self.api, TransmartV2)

    @retry
    def test_get_patients(self):
        patients = self.api.get_patients().get('patients')
        self.assertEqual(4, len(patients))

    @retry
    def test_get_studies(self):
        self.assertIsNone(self.api.studies)
        studies = self.api.get_studies()
        self.assertEqual((9, 4), studies.dataframe.shape)
        self.assertEqual(9, len(self.api.studies))


if __name__ == '__main__':
    unittest.main()
