from pandas.io.json import json_normalize

import google.protobuf.internal.decoder as decoder
from transmart.api.v2.protobuf import observations_pb2 as pb
from google.protobuf.json_format import MessageToJson
import json


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


class ProtobufObservations:
    def __init__(self, data):

        header, cells, footer = self._parse_protobuf(data)

        self.dimension_declarations = json.loads(MessageToJson(header)).get('dimensionDeclarations')
        self.dimensions = json.loads(MessageToJson(footer)).get('dimension')

        self.output_cells = []

        # Build the dimensions dict for easier access later on
        self.dimension_dict = {}
        self._build_dimensions_dict()

        # Organize dimensions
        self.indexed_dimensions = []
        self.inline_dimensions = []
        for dimension in self.dimension_declarations:
            if 'inline' in dimension:
                self.inline_dimensions.append(dimension)
            else:
                self.indexed_dimensions.append(dimension)

        self._parse_cells(cells)

        self.dataframe = json_normalize(self.output_cells)

    def get_declaration(self, name):
        for d in self.dimension_declarations:
            if d.get('name') == name:
                return d

    def _parse_protobuf(self, data):
        # get message length and starting position for the protocol buffer, read header
        length, cursor = decoder._DecodeVarint(data, 0)

        header = pb.Header()
        header.ParseFromString(data[cursor:cursor + length])

        cursor += length
        cells = []
        while True:
            length, cursor = decoder._DecodeVarint(data, cursor)
            cell = pb.Cell()
            cell.ParseFromString(data[cursor:cursor + length])
            cells.append(cell)
            cursor += length

            # Check if the last attribute is set
            if cell.last:
                break

        # run to get the footer
        length, cursor = decoder._DecodeVarint(data, cursor)
        footer = pb.Footer()
        footer.ParseFromString(data[cursor:cursor + length])

        return header, cells, footer

    def _build_dimensions_dict(self):

        for d in self.dimensions:
            d_name = d.get('name')
            d_declaration = self.get_declaration(d_name)

            # Get the names for all fields
            field_names = [f.get('name') for f in d_declaration.get('fields', {})]

            # Transform missing fields to zero based
            missing_fields = [v - 1 for v in d.get('absentFieldColumnIndices', [])]

            fields = d.get('fields')

            if fields:
                n_field_items = len([it for ti in fields[0].values() for it in ti])
            else:
                n_field_items = 0

            # Create list of empty dictionaries
            self.dimension_dict[d_name] = [{} for i in range(n_field_items)]

            for i, field_name in enumerate(field_names):
                for j in range(n_field_items):

                    # Skip value if missing
                    if i in missing_fields:
                        cell_value = None
                    else:
                        # Correct the indices for missing values
                        a = i - sum([i > v for v in missing_fields])
                        cell_value = [it for ti in fields[a].values() for it in ti][j]

                    self.dimension_dict[d_name][j][field_name] = cell_value

    def _parse_cells(self, cells):
        """
        Based on list of Protobuf Cell messages fill th e

        :param cells:
        """
        # Parse list of Protobuf cells
        for cell in cells:
            output_cell = {}
            cell = json.loads(MessageToJson(cell))

            for i, index in enumerate(cell['dimensionIndexes']):
                dimension_name = self.indexed_dimensions[i]['name']

                # 0 means it has no value
                if int(index) == 0:
                    continue

                output_cell[dimension_name] = self.dimension_dict.get(dimension_name)[int(index) - 1]

            for i, index in enumerate(cell.get('inlineDimensions', [])):
                output_cell[self.inline_dimensions[i]['name']] = index

            output_cell['stringValue'] = cell.get('stringValue')
            output_cell['numericValue'] = cell.get('numericValue')

            self.output_cells.append(output_cell)


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

