"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""

import json

from .query_widgets import ConceptPicker, ConstraintWidget


class InvalidConstraint(Exception):
    pass


class Query:
    """ Utility to build queries for transmart v2 api. """

    def __init__(self, handle=None, method='GET', params=None, hal=False,
                 in_study=None, in_patientset=None, in_concept=None, in_gene_list=None,
                 in_transcript_list=None, operator="and"):
        self.handle = handle
        self.method = method
        self.hal = hal
        self._params = params or {}
        self.json = None

        # Operator for constraints, default is and
        self.operator = operator

        # Subject constraints
        self.in_study = StudyConstraint(in_study)
        self.in_patientset = PatientSetConstraint(in_patientset)
        self.set_concept_constraint(in_concept)

        # Biomarker constraints
        self.in_gene_list = GenesConstraint(in_gene_list)
        self.in_transcript_list = TranscriptConstraint(in_transcript_list)

    @property
    def params(self):
        return self._params

    @params.getter
    def params(self):
        self._params.update(self.get_constraints())
        self._params.update(self.get_biomarker_constraints())
        return self._params

    @property
    def headers(self):
        return {'Accept': 'application/{};charset=UTF-8'.format('hal+json' if self.hal else 'json')}

    def get_constraints(self):
        constraints = []
        for c in (self.in_study, self.in_patientset, self.in_concept):
            if isinstance(c, list):
                for v in c:
                    constraints.append(v.get_constraint())
            elif c.value:
                constraints.append(c.get_constraint())

        if len(constraints) > 1:
            constraints = {'constraint': json.dumps({"type" : self.operator, "args": constraints})}
        elif len(constraints) == 1:
            if self.handle == "/v2/patient_sets":
                constraints = {'constraint': constraints[0]}
            else:
                constraints = {'constraint': json.dumps(constraints[0])}
        else:
            constraints = {}
        return constraints

    def get_biomarker_constraints(self):
        constraints = ''.join([str(c) for c in (self.in_transcript_list, self.in_gene_list) if c.value])

        if constraints:
            return {'biomarker_constraint': constraints}
        else:
            return {}

    def __repr__(self):
        return "<Query(handle={}, method={}, params={})>".format(self.handle,
                                                                 self.method,
                                                                 self.params)

    def set_concept_constraint(self, in_concept):
        if isinstance(in_concept, list):
            self.in_concept = []
            for concept_constraint in in_concept:
                if "\\" in concept_constraint:
                    self.in_concept.append(ConceptPathConstraint(concept_constraint))
                else:
                    self.in_concept.append(ConceptCodeConstraint(concept_constraint))
        else:
            if in_concept and "\\" in in_concept:
                self.in_concept = ConceptPathConstraint(in_concept)
            else:
                self.in_concept = ConceptCodeConstraint(in_concept)


class Constraint:

    def __init__(self, value):
        self.value = value

    @property
    def type_(self):
        raise NotImplementedError

    @property
    def val_name(self):
        raise NotImplementedError

    def __str__(self):
        return json.dumps(self.get_constraint())

    def get_constraint(self):
        return {'type': self.type_, self.val_name: self.value}


class FieldConstraint:
    def __init__(self, value):
        self.value = value

    @property
    def type_(self):
        raise NotImplementedError

    @property
    def dimension(self):
        raise NotImplementedError

    @property
    def fieldName(self):
        raise NotImplementedError

    @property
    def operator(self):
        raise NotImplementedError

    def __str__(self):
        return json.dumps(self.get_constraint())

    def get_constraint(self):
        return {'type': 'field',
                'field': {
                    'dimension': self.dimension,
                    'fieldName': self.fieldName,
                    'type': self.type_},
                'operator': self.operator,
                'value': self.value}


class StudyConstraint(Constraint):
    type_ = 'study_name'
    val_name = 'studyId'


class PatientSetConstraint(Constraint):
    type_ = 'patient_set'
    val_name = 'patientSetId'


class ConceptPathConstraint(Constraint):
    type_ = 'concept'
    val_name = 'path'


class ConceptCodeConstraint(Constraint):
    type_ = 'concept'
    val_name = 'conceptCode'


class BiomarkerConstraint(Constraint):

    def __str__(self):
        return json.dumps({"type": "biomarker",
                           "biomarkerType": self.type_,
                           "params": {"names": self.value}})


class TranscriptConstraint(BiomarkerConstraint):
    type_ = 'transcripts'


class GenesConstraint(BiomarkerConstraint):
    type_ = 'genes'


class TrialVisitConstraint(FieldConstraint):
    type_ = 'NUMERIC'
    dimension = 'trial visit'
    fieldName = 'id'
    operator = 'in'


class ObservationConstraint:
    """
    Represents constraints on observation level. This is the set of
    observations that adhere to all criteria specified. A patient set
    based on these constraints can be combined with other sets to
    create complex queries.
    """
    params = ('concept', 'study', 'trial_visit', 'min_value',
              'max_value', 'min_start_date', 'max_start_date')

    def __init__(self,
                 concept: str=None,
                 study: str=None,
                 trial_visit: list=None,
                 min_value=None,
                 max_value=None,
                 min_start_date=None,
                 max_start_date=None,
                 api = None):
        """
        Represents constraints on observation level. This is the set of
        observations that adhere to all criteria specified. A patient set
        based on these constraints can be combined with other sets to
        create complex queries.

        :param concept:
        :param study:
        :param trial_visit:
        :param min_value:
        :param max_value:
        :param min_start_date:
        :param max_start_date:
        """

        self.__concept = concept
        self.__trial_visit = trial_visit
        self.study = study
        self.min_value = min_value
        self.max_value = max_value
        self.min_start_date = min_start_date
        self.max_start_date = max_start_date
        self.api = api

        self._details_widget = ConstraintWidget(self)
        self._aggregates = None

    def __len__(self):
        len_ = 0
        for arg in self.params:
            if getattr(self, arg) is not None:
                len_ += 1

        return len_

    def __repr__(self):
        arguments = []
        for arg in self.params:
            if getattr(self, arg) is not None:
                arguments.append(
                    '{}={}'.format(arg, getattr(self, arg))
                )

        return '{}({})'.format(
            self.__class__.__name__,
            ', '.join(arguments))

    def __str__(self):
        return json.dumps(self.json())

    def __and__(self, other):
        return self.__grouper_logic(other, is_and=True)

    def __or__(self, other):
        return self.__grouper_logic(other, is_and=False)

    def __grouper_logic(self, other, is_and):
        my_type, not_my_type = ('and', 'or') if is_and else ('or', 'and')

        if isinstance(other, self.__class__):
            return GroupConstraint([self, other], my_type)

        if isinstance(other, GroupConstraint):
            if other.group_type == my_type:
                other.items.append(self)
                return other
            if other.group_type == not_my_type:
                return GroupConstraint([self, other], my_type)

    @property
    def trial_visit(self):
        return self.__trial_visit

    @trial_visit.setter
    def trial_visit(self, value):
        if value is None or isinstance(value, list):
            self.__trial_visit = value
        else:
            raise ValueError('Expected list of trial visits is required.')

    @property
    def concept(self):
        return self.__concept

    @concept.setter
    def concept(self, value):
        self._set_concept_code(value)

    def _set_concept_code(self, value):

        # Reset current constraints.
        for arg in self.params:
            if arg != 'concept':
                setattr(self, arg, None)

        self._details_widget.set_initial()

        self.__concept = value

        if self.api is not None:
            self._aggregates = self.api.aggregates_per_concept(self)
            agg = self._aggregates.get('aggregatesPerConcept', {}).get(self.concept, {})
            self._details_widget.update_from_aggregates(agg)

    def find_concept(self):
        if self.api is None:
            raise AttributeError('{}.api not set. Cannot be interactive.'.format(self.__class__))

        return ConceptPicker(target=self._set_concept_code, api=self.api).get()

    def interact(self):
        return self._details_widget.get()

    def json(self):
        args = []

        if len(self) == 0:
            args.append({"type": "true"})

        if self.study is not None:
            args.append(
                StudyConstraint(self.study).get_constraint()
            )

        if self.concept is not None:
            args.append(
                ConceptCodeConstraint(self.concept).get_constraint()
            )

        if self.trial_visit is not None:
            args.append(
                TrialVisitConstraint(list(self.trial_visit)).get_constraint()
            )

        if len(self) > 1:
            constraint = dict()
            constraint['args'] = args
            constraint['type'] = 'and'

        else:
            constraint = args.pop()

        return {'constraint': constraint}


class GroupConstraint:
    def __init__(self, items, group_type):
        self.items = items
        self.group_type = group_type

    def __repr__(self):
        return '{}({})'.format(self.group_type, self.items)

    def __and__(self, other):
        return self.__grouper_logic(other, is_and=True)

    def __or__(self, other):
        return self.__grouper_logic(other, is_and=False)

    def __grouper_logic(self, other, is_and):
        my_type, not_my_type = ('and', 'or') if is_and else ('or', 'and')

        if isinstance(other, ObservationConstraint):
            if self.group_type == my_type:
                self.items.append(other)
                return self
            else:
                return GroupConstraint([self, other], my_type)

        elif isinstance(other, self.__class__):
            if other.group_type == my_type:
                other.items += self.items
                return other
            if other.group_type == not_my_type and self.group_type == my_type:
                self.items.append(other)
                return self
            else:
                return GroupConstraint([self, other], my_type)




# {
#   "type": "subselection",
#   "dimension": "patient",
#   "constraint": {
#   }
# }
#
# {"type": "field", "field": {
#     "dimension": "trial visit", "fieldName": "id", "type":"NUMERIC"},
#  "operator": "in", "value":[27,28,31,32]}

# {
#   "type": "subselection",
#   "dimension": "patient",
#   "constraint": {
#     "type": "and",
#     "args": [
#       {
#         "type": "and",
#         "args": [
#           {
#             "type": "concept",
#             "conceptCode": "spake9"
#           },
#           {
#             "type": "value",
#             "valueType": "NUMERIC",
#             "operator": ">=",
#             "value": 3
#           }
#         ]
#       },
#       {
#         "type": "study_name",
#         "studyId": "ANTR_9"
#       }
#     ]
#   }
# }
#
# {
#   "type": "subselection",
#   "dimension": "patient",
#   "constraint": {
#     "type": "and",
#     "args": [
#       {
#         "type": "and",
#         "args": [
#           {
#             "type": "concept",
#             "conceptCode": "spake9"
#           },
#           {
#             "type": "value",
#             "valueType": "NUMERIC",
#             "operator": ">=",
#             "value": 3
#           },
#           {
#             "type": "value",
#             "valueType": "NUMERIC",
#             "operator": "<=",
#             "value": 5
#           }
#         ]
#       },
#       {
#         "type": "study_name",
#         "studyId": "ANTR_9"
#       }
#     ]
#   }
# }
#
# {
#   "type": "and",
#   "args": [
#     {
#       "type": "subselection",
#       "dimension": "patient",
#       "constraint": {
#         "type": "and",
#         "args": [
#           {
#             "type": "concept",
#             "conceptCode": "sex"
#           },
#           {
#             "type": "or",
#             "args": [
#               {
#                 "type": "value",
#                 "valueType": "STRING",
#                 "operator": "=",
#                 "value": "female"
#               },
#               {
#                 "type": "value",
#                 "valueType": "STRING",
#                 "operator": "=",
#                 "value": "male"
#               }
#             ]
#           }
#         ]
#       }
#     },
#     {
#       "type": "subselection",
#       "dimension": "patient",
#       "constraint": {
#         "type": "concept",
#         "conceptCode": "sex"
#       }
#     }
#   ]
# }