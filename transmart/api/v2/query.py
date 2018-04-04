"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""

from functools import wraps

import json

from .query_widgets import ConceptPicker, ConstraintWidget


class InvalidConstraint(Exception):
    pass


def input_check(types):
    """
    :param types: tuple of allowed types.
    :return: decorator that validates input of property setter.
    """

    if not isinstance(types, tuple):
        raise ValueError('Input check types has to be tuple, got {!r}'.format(type(types)))

    def input_check_decorator(fn):
        @wraps(fn)
        def wrapper(value):
            if value is not None:
                if type(value) not in types:
                    raise ValueError('Expected type {!r} for {!r}, but got {!r}'.
                                     format(types, fn, type(value)))
                else:
                    return value
        return wrapper
    return input_check_decorator


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
        self.in_concept = in_concept

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
                    constraints.append(v.json())
            elif c.value:
                constraints.append(c.json())

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
        return json.dumps(self.json())

    def json(self):
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
        return json.dumps(self.json())

    def json(self):
        return {'type': 'field',
                'field': {
                    'dimension': self.dimension,
                    'fieldName': self.fieldName,
                    'type': self.type_},
                'operator': self.operator,
                'value': self.value}


class ValueConstraint:

    def __init__(self, value):
        self.value = value

    @property
    def value_type_(self):
        raise NotImplementedError

    @property
    def operator(self):
        raise NotImplementedError

    def json(self):
        return {'type': 'value',
                'valueType': self.value_type_,
                'operator': self.operator,
                'value': self.value}


class ValueListConstraint(ValueConstraint):
    value_type_ = 'STRING'
    operator = 'in'


class MinValueConstraint(ValueConstraint):
    value_type_ = 'NUMERIC'
    operator = '>='


class MaxValueConstraint(ValueConstraint):
    value_type_ = 'NUMERIC'
    operator = '<='


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
    params = {'concept': ConceptCodeConstraint,
              'study': StudyConstraint,
              'trial_visit': TrialVisitConstraint,
              'min_value': MinValueConstraint,
              'max_value': MaxValueConstraint,
              'value_list': ValueListConstraint,
              'min_start_date': MinValueConstraint,
              'max_start_date': MaxValueConstraint
              }

    def __init__(self,
                 concept: str=None,
                 study: str=None,
                 trial_visit: list=None,
                 min_value=None,
                 max_value=None,
                 value_list=None,
                 min_start_date=None,
                 max_start_date=None,
                 api=None):
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

        self.__concept = None
        self.__trial_visit = None
        self.__value_list = None
        self.__min_value = None
        self.__max_value = None
        self.__min_start_date = None
        self.__max_start_date = None
        self._dimension_elements = None
        self._aggregates = None

        self.api = api

        if api is not None:
            self._details_widget = ConstraintWidget(self)

        self.concept = concept
        self.trial_visit = trial_visit
        self.value_list = value_list
        self.study = study
        self.min_value = min_value
        self.max_value = max_value
        self.min_start_date = min_start_date
        self.max_start_date = max_start_date

    def __len__(self):
        len_ = 0
        for arg in self.params.keys():
            if getattr(self, arg) is not None:
                len_ += 1

        return len_

    def __repr__(self):
        arguments = []
        for arg in self.params.keys():
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

    def json(self):
        args = []

        if len(self) == 0:
            args.append({"type": "true"})

        for param, constraint in self.params.items():
            attr = getattr(self, param)
            if attr is not None:
                args.append(constraint(attr).json())

        if len(self) > 1:
            constraint = dict()
            constraint['args'] = args
            constraint['type'] = 'and'

        else:
            constraint = args.pop()

        return {'constraint': constraint}

    def subselect(self, dimension='patients'):
        """
        Query that represents all dimension elements that adhere to the
        observation constraints, e.g. all patients that have observations
        for which the criteria apply.

        :param dimension: only patients is supported for now.
        :return:
        """
        d = {'type': 'subselection', 'dimension': dimension}
        d.update(self.json())
        return d

    @property
    def trial_visit(self):
        return self.__trial_visit

    @input_check((list, ))
    @trial_visit.setter
    def trial_visit(self, value):
        self.__trial_visit = value

    @property
    def value_list(self):
        return self.__value_list

    @input_check((list, ))
    @value_list.setter
    def value_list(self, value):
        self.__value_list = value

    @property
    def min_value(self):
        return self.__min_value

    @input_check((int, float))
    @min_value.setter
    def min_value(self, value):
        self.__min_value = value

    @property
    def max_value(self):
        return self.__max_value

    @input_check((int, float))
    @max_value.setter
    def max_value(self, value):
        self.__max_value = value

    @property
    def concept(self):
        return self.__concept

    @concept.setter
    def concept(self, value):
        self.__concept = value

    @property
    def max_start_date(self):
        return self.__max_start_date

    @input_check((str, ))
    @max_start_date.setter
    def max_start_date(self, value):
        self.__max_start_date = value

    @property
    def min_start_date(self):
        return self.__min_start_date

    @input_check((str, ))
    @min_start_date.setter
    def min_start_date(self, value):
        self.__min_start_date = value

    def apply_tree_node_constraints(self, constraints):
        """
        Reset current argument and apply those from a tree node constraints dict.

        :param constraints: constraints from tree node.
        """

        keyword_map = [
            ('concept', 'conceptCode'),
            ('study', 'studyId')
        ]

        if not constraints:
            raise ValueError('Expected dict, got {!r}'.format(type(constraints)))

        # Reset current constraints.
        for arg in self.params.keys():
            setattr(self, arg, None)

        try:
            constraint_list = constraints['args']

        except KeyError:
            constraint_list = [constraints]

        for c in constraint_list:
            for kw in keyword_map:
                if c.get(kw[1]):
                    setattr(self, kw[0], c.get(kw[1]))

        if self.api is not None:
            self.fetch_updates()

    def _dimension_elements_watcher(self):

        def watcher(key, value):
            if value is None:
                return

            if key == 'trial visit':
                options = []
                for tv in value:
                    label = tv.get('relTimeLabel')

                    if tv.get('relTime') or tv.get('relTimeUnit'):
                        label += ' ({} {})'.format(tv.get('relTime'), tv.get('relTimeUnit'))

                    options.append(
                        (label, tv.get('id'))
                    )

                self._details_widget.trial_visit_select.options = sorted(options)
                self._details_widget.trial_visit_select.rows = min(len(options) + 1, 5)

            if key == 'start time':
                pass

        class DictWatcher(dict):
            def __setitem__(self, key, value):
                watcher(key, value)
                super().__setitem__(key, value)

        return DictWatcher()

    def fetch_updates(self):

        if self.api is not None:
            self._details_widget.set_initial()

            agg_response = self.api.aggregates_per_concept(self)
            self._aggregates = agg_response.get('aggregatesPerConcept', {}).get(self.concept, {})
            self._details_widget.update_from_aggregates(self._aggregates)

            self._dimension_elements = self._dimension_elements_watcher()
            for dimension in ('trial visit', 'study', 'start time'):
                self._dimension_elements[dimension] = self.api.dimension_elements(dimension, self).get('elements')

    def find_concept(self):
        if self.api is None:
            raise AttributeError('{}.api not set. Cannot be interactive.'.format(self.__class__))

        return ConceptPicker(target=self.apply_tree_node_constraints, api=self.api).get()

    def interact(self):
        return self._details_widget.get()


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

    def json(self):
        return {
          'type': 'subselection',
          'dimension': 'patient',
          'constraint': {
            "type": self.group_type,
            "args": [item.subselect() for item in self.items]}
        }
