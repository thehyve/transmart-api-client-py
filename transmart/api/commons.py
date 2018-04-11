from hashlib import sha1


def get_dict_identity(dictionary, fields=None):
    """ Calculate a single sha1 for a nested dictionary. """

    identity = sha1()

    def update(value):
        identity.update(str(value).encode())

    def recurse(d):
        for key, value in sorted(d.items()):
            if fields and key not in fields:
                continue

            elif isinstance(value, dict):
                update(key)
                update(get_dict_identity(value, fields))

            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        update(get_dict_identity(item, fields))
                    else:
                        update(item)
            else:
                update(key)
                update(value)

    recurse(dictionary)
    return identity.hexdigest()
