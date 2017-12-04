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
                 in_transcript_list=None, operator="and"):
        self.handle = handle
        self.method = method
        self.hal = hal
        self._params = params or {}

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

    def __str__(self):
        return json.dumps({"type": self.type_, self.val_name: self.value})

    def get_constraint(self):
        return {"type": self.type_, self.val_name: self.value}


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
