from debsources.utils import path_join

from debsources.consts import PREFIXES_DEFAULT


def get_packages_prefixes(cache_dir):
    """
    returns the packages prefixes (a, b, ..., liba, libb, ..., y, z)
    cache_dir: the cache directory, usually comes from the app config
    """
    try:
        with open(path_join(cache_dir, 'pkg-prefixes')) as f:
            prefixes = [l.rstrip() for l in f]
    except IOError:
        prefixes = PREFIXES_DEFAULT
    return prefixes

