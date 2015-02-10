from sqlalchemy import func as sql_func

from debsources.consts import PREFIXES_DEFAULT
from debsources.exceptions import InvalidPackageOrVersionError
from debsources.utils import path_join

from .models import Package, PackageName, Suite, Ctag, File, Checksum


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


def search_query(session, query, suite):
    if not suite:
        exact_matching = (session.query(PackageName)
                            .filter_by(name=query)
                            .first())

        other_results = (session.query(PackageName)
                            .filter(sql_func.lower(PackageName.name)
                                    .contains(query.lower()))
                            .order_by(PackageName.name)
                            )
    else:
        exact_matching = (session.query(PackageName)
                            .filter(sql_func.lower(Suite.suite)
                                    == suite)
                            .filter(Suite.package_id == Package.id)
                            .filter(Package.name_id == PackageName.id)
                            .filter(PackageName.name == query)
                            .first())

        other_results = (session.query(PackageName)
                            .filter(sql_func.lower(Suite.suite)
                                    == suite)
                            .filter(Suite.package_id == Package.id)
                            .filter(Package.name_id == PackageName.id)
                            .filter(sql_func.lower(PackageName.name)
                                    .contains(query.lower()))
                            .order_by(PackageName.name))

    return exact_matching, other_results


def find_ctag(session, ctag, package=None, slice_=None):
    """
    Returns places in the code where a ctag is found.
            tuple (count, [sliced] results)
    session: an SQLAlchemy session
    ctag: the ctag to search
    package: limit results to package
    """

    results = (session.query(PackageName.name.label("package"),
                                Package.version.label("version"),
                                Ctag.file_id.label("file_id"),
                                File.path.label("path"),
                                Ctag.line.label("line"))
                .filter(Ctag.tag == ctag)
                .filter(Ctag.package_id == Package.id)
                .filter(Ctag.file_id == File.id)
                .filter(Package.name_id == PackageName.id)
                )
    if package is not None:
        results = results.filter(PackageName.name == package)

    results = results.order_by(Ctag.package_id, File.path)
    count = results.count()
    if slice_ is not None:
        results = results.slice(slice_[0], slice_[1])
    results = [dict(package=res.package,
                    version=res.version,
                    path=res.path,
                    line=res.line)
                for res in results.all()]
    return (count, results)


def files_with_sum(session, checksum, slice_=None, package=None):
    """
    Returns a list of files whose hexdigest is checksum.
    You can slice the results, passing slice=(start, end).
    """
    results = (session.query(PackageName.name.label("package"),
                                Package.version.label("version"),
                                Checksum.file_id.label("file_id"),
                                File.path.label("path"))
                .filter(Checksum.sha256 == checksum)
                .filter(Checksum.package_id == Package.id)
                .filter(Checksum.file_id == File.id)
                .filter(Package.name_id == PackageName.id)
                )
    if package is not None and package != "":
        results = results.filter(PackageName.name == package)

    results = results.order_by("package", "version", "path")

    if slice_ is not None:
        results = results.slice(slice_[0], slice_[1])
    results = results.all()

    return [dict(path=res.path,
                    package=res.package,
                    version=res.version)
            for res in results]


def checksum_count(session, checksum, package=None):
    # we count the number of results:
    count = (session.query(sql_func.count(Checksum.id))
                .filter(Checksum.sha256 == checksum))
    if package is not None and package != "":  # (only within the package)
        count = (count.filter(PackageName.name == package)
                    .filter(Checksum.package_id == Package.id)
                    .filter(Package.name_id == PackageName.id))
    count = count.first()[0]
    return count
