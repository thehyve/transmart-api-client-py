import jwt

access_token = jwt.encode({'sub': '54604e3b-4d6a-419d-9173-4b1af0530bfb'}, 'secret', algorithm='HS256')

POST_JSON_RESPONSES = {
    '/oauth/token':  {
        'access_token': access_token,
        'token_type': 'bearer',
        'expires_in': 42695,
        'scope': 'read write'},
    '/auth/realms/test/protocol/openid-connect/token':  {
        'access_token': access_token,
        'token_type': 'bearer',
        'expires_in': 42695,
        'scope': 'read write'},
    '/v2/patients': {
        'patients': [
            {'age': 26,
             'birthDate': None,
             'deathDate': None,
             'id': -60,
             'inTrialId': '1',
             'maritalStatus': None,
             'race': 'Caucasian',
             'religion': None,
             'sex': 'MALE',
             'subjectIds': {"SUBJ_ID": "GEORGE"},
             'trial': 'CATEGORICAL_VALUES'},
            {'age': 24,
             'birthDate': None,
             'deathDate': None,
             'id': -50,
             'inTrialId': '2',
             'maritalStatus': None,
             'race': 'Latino',
             'religion': None,
             'sex': 'MALE',
             'subjectIds': {"SUBJ_ID": "PAUL"},
             'trial': 'CATEGORICAL_VALUES'},
            {'age': 20,
             'birthDate': None,
             'deathDate': None,
             'id': -40,
             'inTrialId': '3',
             'maritalStatus': None,
             'race': 'Caucasian',
             'religion': None,
             'sex': 'FEMALE',
             'subjectIds': {"SUBJ_ID": "JOHN"},
             'trial': 'CATEGORICAL_VALUES'},
            {'age': 26,
             'birthDate': None,
             'deathDate': None,
             'id': -61,
             'inTrialId': '1',
             'maritalStatus': None,
             'race': 'Caucasian',
             'religion': None,
             'sex': 'MALE',
             'subjectIds': {"SUBJ_ID": "RINGO"},
             'trial': 'CLINICAL_TRIAL'}]}
}

GET_JSON_RESPONSES = {
    '/v2/studies': {
        'studies': [
            {'bioExperimentId': -10,
             'dimensions': ['patient', 'concept', 'study'],
             'id': -20,
             'studyId': 'CATEGORICAL_VALUES'},
            {'bioExperimentId': -24, 'dimensions': [], 'id': -44, 'studyId': 'MIX_HD'},
            {'bioExperimentId': -28,
             'dimensions': ['patient', 'concept', 'study'],
             'id': -45,
             'studyId': 'ORACLE_1000_PATIENT'},
            {'bioExperimentId': -17,
             'dimensions': ['patient', 'concept', 'study'],
             'id': -27,
             'studyId': 'SHARED_CONCEPTS_STUDY_A'},
            {'bioExperimentId': -18,
             'dimensions': ['patient', 'concept', 'study'],
             'id': -28,
             'studyId': 'SHARED_CONCEPTS_STUDY_B'},
            {'bioExperimentId': -19,
             'dimensions': ['patient', 'concept', 'study'],
             'id': -29,
             'studyId': 'SHARED_CONCEPTS_STUDY_C_PRIV'},
            {'bioExperimentId': -25,
             'dimensions': [],
             'id': -14,
             'studyId': 'SHARED_HD_CONCEPTS_STUDY_A'},
            {'bioExperimentId': -26,
             'dimensions': [],
             'id': -15,
             'studyId': 'SHARED_HD_CONCEPTS_STUDY_B'},
            {'bioExperimentId': -27,
             'dimensions': [],
             'id': -16,
             'studyId': 'SHARED_HD_CONCEPTS_STUDY_C_PR'}]},
}
