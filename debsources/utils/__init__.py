import os

path_join = os.path.join


def extract_stats(filter_suites=None, filename="cache/sources_stats.data"):
    """
    Extracts information from the collected stats.
    If filter_suites is None, all the information are extracted.
    Otherwise suites must be an array of suites names (can contain "total").
    e.g. extract_stats(filter_suites=["total", "debian_wheezy"])
    """
    from debsources import statistics

    res = dict()
    stats = statistics.load_metadata_cache(filename)
    for (key, value) in stats.iteritems():
        splits = key.split(".")
        # if this key/value is in the required suites, we add it
        if filter_suites is None or splits[0] in filter_suites:
            res[key] = value

    return res


# TODO we should use methods like LRU to avoid this un-necessary disk I/O
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

