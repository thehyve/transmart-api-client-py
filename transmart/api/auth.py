import abc
import requests
from getpass import getpass


class Authenticator(metaclass=abc.ABCMeta):

    def __init__(self, url, offline_token=None, realm=None, client_id=None):
        self.url = url
        self.offline_token = offline_token
        self.realm = realm
        self.client_id = client_id or self._default_client_id
        self._access_token = None
        self.get_token()

    @property
    @abc.abstractmethod
    def _default_client_id(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def access_token(self) -> str:
        pass

    @abc.abstractmethod
    def get_token(self):
        pass

    @abc.abstractmethod
    def refresh(self):
        pass


class LegacyAuth(Authenticator):
    _default_client_id = 'glowingbear-js'

    @property
    def access_token(self):
        return self.get_token

    def get_token(self):
        user = input('Username: ')
        r = requests.post(
            "{}/oauth/token".format(self.url),
            params=dict(
                grant_type='password',
                client_id=self.client_id,
                username=user
            ),
            data=dict(
                password=getpass("tranSMART password: ")
            )
        )

        r.raise_for_status()

        self._access_token = r.json().get('access_token')

    def refresh(self):
        self.get_token()


class KeyCloakAuth(Authenticator):
    _default_client_id = 'transmart-client'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def handle(self):
        return '{}/auth/realms/{}/protocol/openid-connect/token'.format(self.url, self.realm)

    @property
    def access_token(self):
        if not self._access_token:
            self.get_token()

        return self._access_token

    def get_token(self):
        offline_token = self.offline_token or input('Offline token: ')
        r = requests.post(
            url=self.handle,
            data=dict(
                grant_type='refresh_token',
                refresh_token=offline_token,
                client_id=self.client_id,
                scope='offline_access',
            )
        )

        if not r.ok:
            r.raise_for_status()

        self._access_token = r.json().get('access_token')

    def refresh(self):
        self.get_token()


def get_auth(host, offline_token=None, kc_url=None, kc_realm=None, client_id=None) -> Authenticator:
    """
    Returns appropriate authenticator depending on the provided parameter.
    If kc_url is provided returns the KeyCloakAuth, else LegacyAuth.

    :param host: transmart api host.
    :param offline_token: offline_token for authentication, will be asked if not provided.
    :param kc_url: KeyCloak hostname (e.g. https://keycloak-test.thehyve.net)
    :param kc_realm: Realm that is registered for the transmart api host to listen.
    :param client_id: client id in keycloak.
    :return: Authenticator
    """

    if kc_url:
        return KeyCloakAuth(url=kc_url,
                            realm=kc_realm,
                            offline_token=offline_token,
                            client_id=client_id)
    else:
        return LegacyAuth(host, client_id)
