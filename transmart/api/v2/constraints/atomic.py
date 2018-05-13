"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""

import json

import arrow
import abc

from ...commons import date_to_timestamp, input_check

END_OF_DAY_FMT = 'YYYY-MM-DDT23:59:59ZZ'
START_OF_DAY_FMT = 'YYYY-MM-DDT00:00:00ZZ'


class Constraint(abc.ABC):

    def __init__(self, value):
        self.value = value

    @property
    @abc.abstractmethod
    def type_(self):
        pass

    @property
    @abc.abstractmethod
    def val_name(self):
        pass

    def __str__(self):
        return json.dumps(self.json())

    def json(self):
        return {'type': self.type_, self.val_name: self.value}


class StudyConstraint(Constraint):
    type_ = 'study_name'
    val_name = 'studyId'


class SubjectSetConstraint(Constraint):
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
    @input_check((list,))
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


class ValueConstraint(abc.ABC):

    def __init__(self, value):
        self.value = value

    @property
    @abc.abstractmethod
    def value_type_(self):
        pass

    @property
    @abc.abstractmethod
    def operator(self):
        pass

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


class MinDateValueConstraint(MinValueConstraint):
    modifier = 0

    def json(self):
        tmp_ = self.value
        try:
            self.value = date_to_timestamp(self.value)
            self.value += self.modifier
            return super().json()

        finally:
            self.value = tmp_


class MaxDateValueConstraint(MaxValueConstraint, MinDateValueConstraint):
    modifier = 24 * 60 * 60 * 1000 - 1  # add 23:59:59:999 in ms


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
    date_fmt = (START_OF_DAY_FMT, END_OF_DAY_FMT)

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
                'values': [arrow.get(d).format(fmt) for d, fmt in zip(self.values, self.date_fmt)]}


class StartTimeBeforeConstraint(StartTimeConstraint):
    operator = '<-'
    n_dates = 1
    date_fmt = (END_OF_DAY_FMT,)


class StartTimeAfterConstraint(StartTimeConstraint):
    operator = '->'
    n_dates = 1
    date_fmt = (START_OF_DAY_FMT,)
