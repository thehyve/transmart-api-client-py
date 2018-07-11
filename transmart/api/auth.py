import abc
import requests
from getpass import getpass
import time


class Authenticator(metaclass=abc.ABCMeta):

    def __init__(self, url, username=None, password=None, realm=None):
        self.url = url
        self.user = username or input('Username: ')
        self.password = password
        self.realm = realm
        self._access_token = None
        self.get_token()

    @property
    @abc.abstractmethod
    def client_id(self):
        pass

    @property
    @abc.abstractmethod
    def access_token(self) -> str:
        pass

    @abc.abstractmethod
    def get_token(self) -> str:
        pass

    @abc.abstractmethod
    def refresh(self):
        pass


class LegacyAuth(Authenticator):
    client_id = 'glowingbear-js'

    @property
    def access_token(self):
        return self._access_token

    def get_token(self):
        r = requests.post(
            "{}/oauth/token".format(self.url),
            params=dict(
                grant_type='password',
                client_id=self.client_id,
                username=self.user
            ),
            data=dict(
                password=self.password or getpass("tranSMART password: ")
            )
        )

        r.raise_for_status()

        self._access_token = r.json().get('access_token')

    def refresh(self):
        self.get_token()


class KeyCloakAuth(Authenticator):
    client_id = 'transmart-api'

    def __init__(self, *args, **kwargs):
        self.refresh_token = None
        self.timeout = None
        super().__init__(*args, **kwargs)

    @property
    def handle(self):
        return '{}/auth/realms/{}/protocol/openid-connect/token'.format(self.url, self.realm)

    @property
    def access_token(self):
        if self.timeout is not None and time.time() > self.timeout:
            self.refresh()

        return self._access_token

    def get_token(self):
        r = requests.post(
            url=self.handle,
            data=dict(
                grant_type='password',
                client_id=self.client_id,
                username=self.user,
                password=self.password or getpass("KeyCloak password: "),
                scope='offline'
            )
        )

        r.raise_for_status()

        if r.json().get('expires_in'):
            self.timeout = time.time() + r.json().get('expires_in')

        self.refresh_token = r.json().get('refresh_token')
        self._access_token = r.json().get('access_token')

    def refresh(self):
        r = requests.post(
            url=self.handle,
            data=dict(
                grant_type='refresh_token',
                refresh_token=self.refresh_token,
                client_id=self.client_id,
            )
        )

        if r.json().get('error') == 'invalid_grant':
            self.get_token()
            return

        if r.json().get('expires_in'):
            self.timeout = time.time() + r.json().get('expires_in')

        self._access_token = r.json().get('access_token')


def get_auth(host, user=None, password=None, kc_url=None, kc_realm=None) -> Authenticator:
    """
    Returns appropriate authenticator depending on the provided parameter.
    If kc_url is provided returns the KeyCloakAuth, else LegacyAuth.

    :param host: transmart api host.
    :param user: username for authentication, will be asked if not provided.
    :param password: password for authentication, will be asked if not provided.
    :param kc_url: KeyCloak hostname (e.g. https://keycloak-test.thehyve.net)
    :param kc_realm: Realm that is registered for the transmart api host to listen.
    :return: Authenticator
    """

    if kc_url:
        return KeyCloakAuth(url=kc_url,
                            realm=kc_realm,
                            username=user,
                            password=password,
                            )
    else:
        return LegacyAuth(host, user, password)
