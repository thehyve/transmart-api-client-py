import unittest
from transmart.api.v2.data_structures import ObservationSet
import pandas as pd
import pandas.testing as pdt


class ObservationSetTestCase(unittest.TestCase):

    def test_get_empty_df(self):
        observations_api_response = {
            'dimensionDeclarations': [],
            'cells': [],
            'dimensionElements': {}
        }

        df = ObservationSet(observations_api_response).dataframe

        self.assertIsNotNone(df)
        self.assertEqual(df.size, 0)
        self.assertEqual(len(df.columns), 0)

    def test_df_shape(self):
        observations_api_response = {
            'dimensionDeclarations': [
                {
                    'name': 'dim1',
                },
                {
                    'name': 'dim2',
                },
            ],
            'cells': [
                {
                    'inlineDimensions': [],
                    'dimensionIndexes': [
                        1,
                        0,
                    ],
                    'stringValue': 'A'
                },
                {
                    'inlineDimensions': [],
                    'dimensionIndexes': [
                        0,
                        1,
                    ],
                    'numericValue': 25
                }
            ],
            'dimensionElements': {
                'dim1': [
                    {
                        'name': 'dim1 el1',
                    },
                    {
                        'name': 'dim1 el2',
                    },
                ],
                'dim2': [
                    {
                        'name': 'dim2 el1',
                    },
                    {
                        'name': 'dim2 el2',
                    },
                ],
            }
        }

        df = ObservationSet(observations_api_response).dataframe

        self.assertIsNotNone(df)
        pdt.assert_frame_equal(df, pd.DataFrame([
            {'dim1.name': 'dim1 el2', 'dim2.name': 'dim2 el1', 'stringValue': 'A'},
            {'dim1.name': 'dim1 el1', 'dim2.name': 'dim2 el2', 'numericValue': 25},
        ]))
