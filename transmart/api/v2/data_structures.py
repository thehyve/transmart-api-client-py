from pandas.io.json import json_normalize


class ObservationSet:
    """ Class to represent observation sets from tranSMART API v2 """

    def __init__(self, json):
        self.json = json
        self.dataframe = json_normalize(self._format_observations(self.json))

    @property
    def all_concepts(self):
        return self.dataframe.loc[:, 'concept.conceptPath'].unique()

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

    def aggregate_numeric_on_trial_visit(self, concept):
        concept_groups = self.dataframe.groupby('concept.conceptPath')
        concept_group = concept_groups.get_group(concept)
        columns_of_interest = ['patient.inTrialId', 'trial visit.relTimeLabel', 'numericValue']
        df_subset = self.dataframe.loc[:, columns_of_interest]
        df_subset.columns = ['subject', 'visit_label', 'value']
        return df_subset.pivot_table(index='visit_label',
                                     values='value',
                                     columns='subject',
                                     aggfunc='mean')
