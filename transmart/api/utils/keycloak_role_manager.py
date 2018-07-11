import requests
from ..auth import KeyCloakAuth


class KeyCloakRoleManagerException(Exception):
    pass


class KeyCloakRoleManager:
    """
    The logged in user requires 'ROLE_ADMIN' in transmart-api client in KeyCloak to see all studies.

    Also required for this user is the 'manage-clients' role in the 'realm-management' client
    to find the guid corresponding to transmart-api client and add roles.

    Example usage:
    \b
        import transmart as tm
        from transmart.api.utils import KeyCloakRoleManager
        host = 'https://transmart-dev.thehyve.net'
        kc_url = "https://keycloak-dwh-test.thehyve.net"
        kc_realm = "transmart-dev"

        user = 'boris'
        password = None

        api = tm.get_api(
            host = host,
            api_version = 2,
            user = user,
            password = password,
            kc_url=kc_url,
            kc_realm=kc_realm,
            print_urls = True,
            interactive = True
        )

        kc_manager = KeyCloakRoleManager(api)
        # The following adds roles for all studies. To add roles
        # for a specific study use kc_manager.add_single_study_roles()
        kc_manager.add_all_studies()

    """

    # Machine + human readable (for description)
    STUDY_ROLES = {
        'MEASUREMENTS': 'Observations for ',
        'SUMMARY': 'Summary level for ',
        'COUNTS_WITH_THRESHOLD': 'Threshold summary level for '
    }

    def __init__(self, api):
        if not isinstance(api.auth, KeyCloakAuth):
            msg = 'Expected to be authenticated via KeyCloakAuth, but got {}.'.format(type(api.auth))
            raise TypeError(msg)

        self.api = api
        self.url = self.api.auth.url
        self.realm = self.api.auth.realm
        self.client_name = self.api.auth.client_id

        self._client_id = self.get_client_guid()
        self.roles_url = '{}/auth/admin/realms/{}/clients/{}/roles'.format(self.url, self.realm, self._client_id)

    @property
    def _headers(self):
        return {'Authorization': 'Bearer ' + self.api.auth.access_token}

    def get_client_guid(self):
        print('Querying for client guid.')

        r = requests.get(url='{}/auth/admin/realms/{}/clients'.format(self.url, self.realm),
                         headers=self._headers)

        if r.status_code == 403:
            msg = "Access denied. Do you have the 'manage-clients' role in the 'realm-management'?"
            raise KeyCloakRoleManagerException(msg)

        r.raise_for_status()

        clients = [c.get('id') for c in r.json() if c.get('clientId') == self.client_name]
        if len(clients) == 0:
            msg = 'Client {!r} not found in KeyCloak'.format(self.client_name)
            raise KeyCloakRoleManagerException(msg)
        return clients[0]

    @property
    def current_roles(self):
        """ Get the set of all study IDs currently in KeyCloak. """
        r = requests.get(url=self.roles_url, headers=self._headers)
        r.raise_for_status()
        return {
            role['name'].split('|')[0]
            for role in r.json()
        }

    @staticmethod
    def get_role_representation(name, description):
        return {
            "name": name,
            "scopeParamRequired": "",
            "description": description
        }

    def add_single_study_roles(self, study_id, study_description=None):
        if not study_description:
            study_description = study_id

        for role, human_level in self.STUDY_ROLES.items():
            name = '{}|{}'.format(study_id, role)
            desc = human_level + study_description
            r = requests.post(
                url=self.roles_url,
                headers=self._headers,
                json=self.get_role_representation(name, desc))
            r.raise_for_status()
        print('Added roles for {!r}.'.format(study_id))

    def add_all_studies(self):
        # studyId, tree path tuples
        studies = [
            (v.get('studyId'), k)
            for k, v in self.api.tree_dict.items()
            if 'STUDY' in v.get('visualAttributes')
        ]

        current_roles = self.current_roles

        for study, path in studies:
            if study in current_roles:
                print('Already have {!r}, skipping..'.format(study))
                continue

            self.add_single_study_roles(study, path)

