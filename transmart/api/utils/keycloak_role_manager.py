import requests
import logging
import click

from ..auth import KeyCloakAuth

logger = logging.getLogger('tm-api')


class KeyCloakRoleManagerException(Exception):
    pass


class KeyCloakRoleManager:
    """
    The user for whom an offline token was generated requires 'ROLE_ADMIN'
    in transmart-api client in KeyCloak to see all studies.

    Also required for this user is the 'manage-clients' role in the 'realm-management' client
    to find the guid corresponding to transmart-api client and add roles.

    Example usage:
    \b
        import transmart as tm
        from transmart.api.utils import KeyCloakRoleManager
        host = 'https://transmart-dev.thehyve.net'
        kc_url = "https://keycloak-dwh-test.thehyve.net"
        kc_realm = "transmart-dev"

        offline_token = None

        api = tm.get_api(
            host = host,
            api_version = 2,
            offline_token = offline_token,
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
        # 'SUMMARY': 'Summary level for ',
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

    def get_current_roles(self):
        """ Get the set of all study roles currently in KeyCloak. """
        r = requests.get(url=self.roles_url, headers=self._headers)
        r.raise_for_status()
        return {role['name'] for role in r.json()}

    @staticmethod
    def get_role_representation(name, description):
        return {
            "name": name,
            "scopeParamRequired": "",
            "description": description
        }

    def add_single_study_roles(self, study_id: str, study_description: str=None):
        """
        Try to add all roles in self.STUDY_ROLES to KeyCloak for a given
        study id. If the role already exists, nothing happens.

        :param study_id: transmart study_id
        :param study_description: a optional name for the study which will
            be used in the role description in KeyCloak.
        """
        if not study_description:
            study_description = study_id

        for role, human_level in self.STUDY_ROLES.items():
            name = '{}|{}'.format(study_id, role)
            desc = human_level + study_description
            r = requests.post(
                url=self.roles_url,
                headers=self._headers,
                json=self.get_role_representation(name, desc))

            if 200 <= r.status_code <= 299:
                print('Added role {!r} for {!r}.'.format(role, study_id))

    def add_all_studies(self):
        """
        Calls self.add_single_study_roles() for all studies in transmart.
        """
        study_ids = [s.get('studyId') for s in self.api.get_studies(as_json=True).get('studies')
                     if s.get('secureObjectToken') != 'PUBLIC']

        for study in study_ids:
            self.add_single_study_roles(study)


def run_role_manager(transmart, kc_url, realm, offline_token=None, study=None):
    import transmart as tm

    api = tm.get_api(
        host=transmart,
        api_version=2,
        offline_token=offline_token,
        kc_url=kc_url,
        kc_realm=realm,
        print_urls=True,
        interactive=False
    )

    kc_manager = KeyCloakRoleManager(api)
    if study:
        kc_manager.add_single_study_roles(study)
    else:
        kc_manager.add_all_studies()


@click.command()
@click.option('-t', '--transmart', required=True,
              help='tranSMART host url, e.g. https://transmart-dev.thehyve.net.')
@click.option('-k', '--kc-url', required=True,
              help='KeyCloak host, e.g. https://keycloak-dwh-test.thehyve.net.')
@click.option('-r', '--realm', help='KeyCloak realm.', required=True)
@click.option('-o', '--offline-token', help='KeyCloak offline token, will be asked for if not provided.')
@click.option('-s', '--study', default=None,
              help='Add roles for this study IDs. If not provided, add all studies.')
@click.version_option(prog_name="Add roles from tranSMART to KeyCloak.")
def _role_manager_entry_point(*args, **kwargs):
    run_role_manager(*args, **kwargs)
