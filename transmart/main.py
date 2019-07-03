from .api.v1.api import TransmartV1
from .api.v2.api import TransmartV2


def get_api(host, api_version=2,
            offline_token=None, kc_url=None, kc_realm=None,
            print_urls=False, interactive=True, client_id=None, verify=None, **kwargs):
    """
    Create the python transmart client by providing user credentials.

    :param host: a transmart URL (e.g. http://transmart-test.thehyve.net)
    :param api_version: either 1 or 2. Default is 2.
    :param offline_token: if not given, it asks for it.
    :param kc_url: KeyCloak hostname (e.g. https://keycloak-test.thehyve.net)
    :param kc_realm: Realm that is registered for the transmart api host to listen.
    :param print_urls: print the url of handles being used.
    :param interactive: automatically build caches for interactive use.
    :param client_id: client id in keycloak.
    :param verify: Either a boolean, in which case it controls whether we verify
    the server’s TLS certificate, or a string, in which case it must be a path
    to a CA bundle to use. Defaults to True.
    """
    api_versions = (1, 2)

    if api_version not in api_versions:
        raise ValueError("Not a valid TranSMART API version. Choose from: " + str(api_versions))

    api = TransmartV1 if api_version == 1 else TransmartV2

    return api(host=host,
               offline_token=offline_token,
               kc_url=kc_url,
               kc_realm=kc_realm,
               print_urls=print_urls,
               interactive=interactive,
               client_id=client_id,
               verify=verify,
               **kwargs)
