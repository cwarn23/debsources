from sqlalchemy import func as sql_func

from debsources.consts import PREFIXES_DEFAULT
from debsources.exceptions import InvalidPackageOrVersionError
from debsources.utils import path_join

from .models import Package, PackageName, Suite



def pkg_versions(session, packagename, suite=""):
    """
    return all versions of a packagename. if suite is specified, only
    versions contained in that suite are returned.
    """
    try:
        name_id = session.query(PackageName) \
                            .filter(PackageName.name == packagename) \
                            .first().id
    except Exception:
        raise InvalidPackageOrVersionError(packagename)
    try:
        if not suite:
            versions = session.query(Package) \
                                .filter(Package.name_id == name_id).all()
        else:
            versions = (session.query(Package)
                                .filter(Package.name_id == name_id)
                                .filter(sql_func.lower(Suite.suite)
                                        == suite)
                                .filter(Suite.package_id == Package.id)
                                .all())
    except Exception:
        raise InvalidPackageOrVersionError(packagename)
    # we sort the versions according to debian versions rules
    versions = sorted(versions, cmp=version_compare)
    return versions


def pkg_prefixes(session, prefix='a', suite=None):
    if not suite:
        packages = (session.query(PackageName)
                    .filter(sql_func.lower(PackageName.name)
                            .startswith(prefix))
                    .order_by(PackageName.name)
                    .all()
                    )
    else:
        packages = (session.query(PackageName)
                    .filter(sql_func.lower(Suite.suite)
                            == suite)
                    .filter(Suite.package_id == Package.id)
                    .filter(Package.name_id == PackageName.id)
                    .filter(sql_func.lower(PackageName.name)
                            .startswith(prefix))
                    .order_by(PackageName.name)
                    .all()
                    )
    return packages
