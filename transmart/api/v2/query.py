"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""


class Query:
    """ Utility to build queries for transmart v2 api. """

    def __init__(self, handle=None, method='GET', params=None, in_study=None, in_patientset=None, hal=False):
        self.handle = handle
        self.method = method
        self.hal = hal
        self._params = params or {}
        self.in_study = in_study
        self.in_patientset = in_patientset

    @property
    def params(self):
        return self._params

    @params.getter
    def params(self):
        self._params.update(self.get_constraints())
        return self._params

    @property
    def headers(self):
        return {'Accept': 'application/{};charset=UTF-8'.format('hal+json' if self.hal else 'json')}

    def get_constraints(self):
        constraints = ''

        if self.in_study:
            constraints += '{"type":"study_name","studyId":"%s"}' % self.in_study
        if self.in_patientset:
            constraints += '{"type":"patient_set","patientSetId":%s}' % self.in_patientset

        if constraints:
            return {'constraint': constraints}
        else:
            return {}

    def __repr__(self):
        return "<Query(handle={}, method={}, params={})>".format(self.handle,
                                                                 self.method,
                                                                 self.params)
