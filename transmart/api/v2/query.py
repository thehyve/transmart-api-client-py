"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""

import json


class Query:
    """ Utility to build queries for transmart v2 api. """

    def __init__(self, handle=None, method='GET', params=None, hal=False,
                 in_study=None, in_patientset=None, in_concept=None, in_gene_list=None,
                 in_transcript_list=None):
        self.handle = handle
        self.method = method
        self.hal = hal
        self._params = params or {}

        # Subject constraints
        self.in_study = StudyConstraint(in_study)
        self.in_patientset = PatientSetConstraint(in_patientset)
        self.in_concept = ConceptConstraint(in_concept)

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
        constraints = ''.join([str(c) for c in (self.in_study, self.in_patientset, self.in_concept) if c.value])

        if constraints:
            return {'constraint': constraints}
        else:
            return {}

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


class Constraint:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return json.dumps({"type": self.type_, self.val_name: self.value})


class StudyConstraint(Constraint):
    type_ = 'study_name'
    val_name = 'studyId'


class PatientSetConstraint(Constraint):
    type_ = 'patient_set'
    val_name = 'patientSetId'


class ConceptConstraint(Constraint):
    type_ = 'concept'
    val_name = 'path'


class BiomarkerConstraint(Constraint):

    def __str__(self):
        return json.dumps({"type": "biomarker",
                           "biomarkerType": self.type_,
                           "params": {"names": self.value}})


class TranscriptConstraint(BiomarkerConstraint):
    type_ = 'transcripts'


class GenesConstraint(BiomarkerConstraint):
    type_ = 'genes'
