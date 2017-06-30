from pandas.io.json import json_normalize


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


class ObservationSet:
    """ Class to represent observation sets from tranSMART API v2 """

    def __init__(self, json):
        self.json = json
        try:
            self.dataframe = json_normalize(_format_observations(self.json))
        except:
            print(self.json)
            raise

    @property
    def all_concepts(self):
        return self.dataframe.loc[:, 'concept.conceptPath'].unique()

    def aggregate_numeric_on_trial_visit(self, concept):
        concept_groups = self.dataframe.groupby('concept.conceptPath')
        concept_group = concept_groups.get_group(concept)
        columns_of_interest = ['patient.inTrialId', 'trial visit.relTimeLabel', 'numericValue']
        df_subset = concept_group.loc[:, columns_of_interest]
        df_subset.columns = ['subject', 'visit_label', 'value']
        return df_subset.pivot_table(index='visit_label',
                                     values='value',
                                     columns='subject',
                                     aggfunc='mean')


class ObservationSetHD:

    def __init__(self, json):
        self.json = json
        try:
            self.dataframe = json_normalize(_format_observations(self.json))
            assert not self.dataframe.shape == (0, 0)
        except:
            print(self.json)
            raise

    @property
    def all_biomarkers(self):
        return self.dataframe.groupby(['biomarker.biomarker', 'biomarker.label']).size()

    def biomarker_boxplot(self):
        if len(self.all_biomarkers) > 1:
            return self.dataframe.boxplot(column='numericValue', by=['biomarker.biomarker', 'biomarker.label'])


class Studies:

    def __init__(self, json):
        self.json = json
        self.dataframe = json_normalize(json['studies'])


class StudyList:
    def __init__(self, study_list):
        for study_id in study_list:
            self.__dict__[study_id.replace('-', '_')] = study_id


class TreeNodes:

    def __init__(self, json):
        self.json = json

    def __repr__(self):
        return self.pretty()

    def pretty(self, root=None, depth=0, spacing=2):
        """
        Create a pretty representation of tree.
        """
        if root is None:
            root = self.json.get('tree_nodes')[0]
        fmt = "%s%s/" if root.get('children') else "%s%s"
        s = fmt % (" " * depth * spacing, "{}  ({})".format(root.get('name'), root.get('patientCount')))
        for child in root.get('children', {}):
            s += "\n%s" % self.pretty(child, depth + 1, spacing)
        return s


class PatientSets:

    def __init__(self, json):
        self.json = json
        self.dataframe = json_normalize(json.get('patientSets'))

