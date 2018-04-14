"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""
import json

import arrow
from functools import wraps

from .constraint_widgets import ConceptPicker, ConstraintWidget


class InvalidConstraint(Exception):
    pass


def input_check(types):
    """
    :param types: tuple of allowed types.
    :return: decorator that validates input of property setter.
    """
    if not isinstance(types, tuple):
        msg = 'Input check types has to be tuple, got {!r}'.format(type(types))
        raise ValueError(msg)

    def input_check_decorator(func):
        @wraps(func)
        def wrapper(self, value):

            if value is not None:
                if type(value) not in types:
                    raise ValueError('Expected type {!r} for {!r}, but got {!r}'.
                                     format(types, func.__name__, type(value)))
            return func(self, value)
        return wrapper
    return input_check_decorator


def bind_widget_tuple(target, pos):
    """
    :param target: widget to bind to.
    :param pos: position in tuple.
    """
    def bind_decorator(func):
        @wraps(func)
        def wrapper(self, value):
            try:
                if value is not None:
                    w = getattr(self._details_widget, target)
                    with w.hold_sync():

                        state = list(w.value)
                        state[pos] = value
                        w.value = tuple(state)

            except AttributeError:
                pass

            finally:
                return func(self, value)
        return wrapper
    return bind_decorator


def bind_widget_list(target):
    """
    :param target: widget to bind to.
    """
    def bind_decorator(func):
        @wraps(func)
        def wrapper(self, value):
            try:
                w = getattr(self._details_widget, target)
                with w.hold_sync():
                    w.value = () if value is None else tuple(value)

            except AttributeError:
                pass

            finally:
                return func(self, value)
        return wrapper
    return bind_decorator


class Query:
    """ Utility to build queries for transmart v2 api. """

    def __init__(self, handle=None, method='GET', params=None, hal=False, json=None):
        self.handle = handle
        self.method = method
        self.hal = hal
        self.params = params
        self.json = json

    @property
    def headers(self):
        return {'Accept': 'application/{};charset=UTF-8'.format('hal+json' if self.hal else 'json')}


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


class StudyConstraint(Constraint):
    type_ = 'study_name'
    val_name = 'studyId'


class PatientSetConstraint(Constraint):
    type_ = 'patient_set'
    val_name = 'patientSetId'


class ConceptCodeConstraint(Constraint):
    type_ = 'concept'
    val_name = 'conceptCode'


class BiomarkerConstraint:

    def __init__(self, biomarkers: list = None, biomarker_type='genes'):
        self.type_ = biomarker_type
        self.__biomarkers = None

        self.biomarkers = biomarkers

    @property
    def biomarkers(self):
        return self.__biomarkers

    @biomarkers.setter
    @input_check((list, ))
    def biomarkers(self, value):
        self.__biomarkers = value

    def __str__(self):
        return json.dumps(self.json())

    def json(self):
        d_ = dict(type='biomarker',
                  biomarkerType=self.type_)
        if self.biomarkers:
            d_['params'] = {"names": self.biomarkers}

        return d_


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


class MinValueConstraint(ValueConstraint):
    value_type_ = 'NUMERIC'
    operator = '>='


class MaxValueConstraint(ValueConstraint):
    value_type_ = 'NUMERIC'
    operator = '<='


class ValueListConstraint(ValueConstraint):
    value_type_ = 'STRING'
    operator = '='

    def json(self):
        return {'type': 'or',
                'args': [
                    {'type': 'value',
                     'valueType': self.value_type_,
                     'operator': self.operator,
                     'value': value}
                    for value in self.value]
                }


class TrialVisitConstraint:

    def __init__(self, values):
        self.values = values if isinstance(values, list) else [values]

    def __str__(self):
        return json.dumps(self.json())

    def json(self):
        return {'type': 'or',
                'args': [
                    {'type': 'field',
                     'field': {
                         'dimension': 'trial visit',
                         'fieldName': 'id',
                         'type': 'NUMERIC'},
                     'operator': '=',
                     'value': value}
                    for value in self.values]
                }


class StartTimeConstraint:
    operator = '<-->'
    n_dates = 2

    def __init__(self, values):
        self.values = values if isinstance(values, list) else [values]
        if len(self.values) != self.n_dates:
            raise ValueError('Expected {} dates, but got {}, for {!r}.'.
                             format(self.n_dates, len(self.values), self.__class__))

    def json(self):
        return {'type': 'time',
                'field': {
                    'dimension': 'start time',
                    'fieldName': 'startDate',
                    'type': 'DATE'},
                'operator': self.operator,
                'values': [arrow.get(d).isoformat() for d in self.values]}


class StartTimeBeforeConstraint(StartTimeConstraint):
    operator = '<-'
    n_dates = 1


class StartTimeAfterConstraint(StartTimeConstraint):
    operator = '->'
    n_dates = 1


class Queryable:

    def json(self):
        raise NotImplementedError


class ObservationConstraint(Queryable):
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
              'min_start_date': StartTimeAfterConstraint,
              'max_start_date': StartTimeBeforeConstraint
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
                 subselection=None,
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
        :param subselection:
        :param api:
        """

        self.__concept = None
        self.__trial_visit = None
        self.__value_list = None
        self.__min_value = None
        self.__max_value = None
        self.__min_start_date = None
        self.__max_start_date = None
        self.__subselection = None
        self._dimension_elements = None
        self._aggregates = None
        self.study = None

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
        self.subselection = subselection

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

        if self.subselection is not None:
            return dict(type='subselection',
                        dimension=self.subselection,
                        constraint=constraint)

        return constraint

    def subselect(self, dimension='patient'):
        """
        Query that represents all dimension elements that adhere to the
        observation constraints, e.g. all patients that have observations
        for which the criteria apply.

        :param dimension: only patients is supported for now.
        :return: criteria dictionary.
        """
        current = self.subselection
        try:
            self.subselection = dimension
            return self.json()

        finally:
            self.subselection = current

    @property
    def trial_visit(self):
        """
        List of trial visits by id.
        """
        return self.__trial_visit

    @trial_visit.setter
    @input_check((list, ))
    @bind_widget_list('trial_visit_select')
    def trial_visit(self, value):
        self.__trial_visit = value

    @property
    def value_list(self):
        """
        List of categorical options.
        """
        return self.__value_list

    @value_list.setter
    @input_check((list, ))
    @bind_widget_list('categorical_select')
    def value_list(self, value):
        self.__value_list = value

    @property
    def min_value(self):
        """
        Minimum value for numerical concepts, int or float.
        """
        return self.__min_value

    @min_value.setter
    @input_check((int, float))
    @bind_widget_tuple('numeric_range', 0)
    def min_value(self, value):
        self.__min_value = value

    @property
    def max_value(self):
        """
        Maximum value for numerical concepts, int or float.
        """
        return self.__max_value

    @max_value.setter
    @input_check((int, float))
    @bind_widget_tuple('numeric_range', 1)
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

    @max_start_date.setter
    @input_check((str, ))
    def max_start_date(self, value):
        self.__max_start_date = value

    @property
    def min_start_date(self):
        return self.__min_start_date

    @min_start_date.setter
    @input_check((str, ))
    def min_start_date(self, value):
        self.__min_start_date = value

    @property
    def subselection(self):
        return self.__subselection

    @subselection.setter
    @input_check((str, ))
    def subselection(self, value):
        self.__subselection = value

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
                self._details_widget.update_trial_visits(value)

            elif key == 'start time':
                self._details_widget.update_start_time(value)

        class DictWatcher(dict):
            def __setitem__(self, key, value):
                watcher(key, value)
                super().__setitem__(key, value)

        return DictWatcher()

    def fetch_updates(self):

        if self.api is not None and self.api.interactive:
            self._details_widget.set_initial()
            self._details_widget.update_obs_repr()

            agg_response = self.api.aggregates_per_concept(self)
            self._aggregates = agg_response.get('aggregatesPerConcept', {}).get(self.concept, {})

            self._details_widget.update_from_aggregates(self._aggregates)

            self._dimension_elements = self._dimension_elements_watcher()
            for dimension in ('trial visit', 'study', 'start time'):
                self._dimension_elements[dimension] = self.api.dimension_elements(self, dimension).get('elements')

    def find_concept(self, search_string=None):
        """

        :param search_string: Optionally pre-fill the search field
        :return:
        """
        if self.api is None:
            raise AttributeError('{}.api not set. Cannot be interactive.'.format(self.__class__))

        cp = ConceptPicker(target=self.apply_tree_node_constraints, api=self.api)
        cp.search_bar.value = search_string
        return cp.get()

    def interact(self):
        return self._details_widget.get()


class GroupConstraint(Queryable):
    def __init__(self, items, group_type):
        self.items = items
        self.group_type = group_type

    def __str__(self):
        return json.dumps(self.json())

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
            'type': self.group_type,
            'args': [item.subselect() for item in self.items]
        }


class RelationConstraint(Queryable):

    def __init__(self, constraint, type_label):
        self.constraint = constraint
        self.type_label = type_label

    def json(self):
        return {
            "type": "subselection",
            "dimension": "patient",
            "constraint": {
                "type": "relation",
                "relatedSubjectsConstraint": self.constraint.json(),
                "relationTypeLabel": self.type_label,
            }
        }

    def subselect(self):
        return self.json()
