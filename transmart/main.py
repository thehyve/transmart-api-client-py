from .api.v1.tm_api_v1 import TransmartV1
from .api.v2.tm_api_v2 import TransmartV2


def get_api(host, api_version=2, user=None, password=None, print_urls=False):
    """
    Create the python transmart client by providing user credentials.

    :param host: a transmart URL (e.g. http://transmart-test.thehyve.net)
    :param user: if not given, it asks for it.
    :param password: if not given, it asks for it.
    :param api_version: either 1 or 2. Default is 2.
    :param print_urls: print the url of handles being used.
    """
    api_versions = (1, 2)

    if api_version not in api_versions:
        raise ValueError("Not a valid TranSMART API version. Choose from: " + str(api_versions))

    api = TransmartV1 if api_version == 1 else TransmartV2

    return api(host, user=user, password=password, print_urls=print_urls)
