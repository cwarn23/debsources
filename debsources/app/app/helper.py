import os
import magic
import stat
from functools import partial
from math import ceil
from collections import namedtuple

from flask import render_template, request, url_for

from debsources.debmirror import SourcePackage
from debsources.db.models import (
    Package, PackageName, )

from debsources.excepts import (InvalidPackageOrVersionError,
                                FileOrFolderNotFound)

def bind_render(template, **kwargs):
    return partial(render_template, template, **kwargs)


def format_big_num(num):
    try:
        res = "{:,}".format(num)
    except:
        res = num
    return res


class Pagination(object):

    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=5,
                   right_current=5, right_edge=2):
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

    @staticmethod
    def url_for_other_page(page):
        args = dict(request.args.copy())
        args['page'] = page
        return url_for(request.endpoint, **args)


# it's used in Location.get_stat
# to bypass flake8 complaints, we do not inject the global namespace
# with globals()["LongFMT"] = namedtuple...
LongFMT = namedtuple("LongFMT", ["type", "perms", "size", "symlink_dest"])


class Location(object):
    """ a location in a package, can be a directory or a file """

    def _get_debian_path(self, session, package, version, sources_dir):
        """
        Returns the Debian path of a package version.
        For example: main/h
                     contrib/libz
        It's the path of a *version*, since a package can have multiple
        versions in multiple areas (ie main/contrib/nonfree).

        sources_dir: the sources directory, usually comes from the app config
        """
        prefix = SourcePackage.pkg_prefix(package)

        try:
            p_id = session.query(PackageName) \
                          .filter(PackageName.name == package).first().id
            varea = session.query(Package) \
                           .filter(and_(Package.name_id == p_id,
                                        Package.version == version)) \
                           .first().area
        except:
            # the package or version doesn't exist in the database
            # BUT: packages are stored for a longer time in the filesystem
            # to allow codesearch.d.n and others less up-to-date platforms
            # to point here.
            # Problem: we don't know the area of such a package
            # so we try in main, contrib and non-free.
            for area in AREAS:
                if os.path.exists(os.path.join(sources_dir, area,
                                               prefix, package, version)):
                    return os.path.join(area, prefix)

            raise InvalidPackageOrVersionError("%s %s" % (package, version))

        return os.path.join(varea, prefix)

    def __init__(self, session, sources_dir, sources_static,
                 package, version="", path=""):
        """ initialises useful attributes """
        debian_path = self._get_debian_path(session,
                                            package, version, sources_dir)
        self.package = package
        self.version = version
        self.path = path
        self.path_to = os.path.join(package, version, path)

        self.sources_path = os.path.join(
            sources_dir,
            debian_path,
            self.path_to)

        self.version_path = os.path.join(
            sources_dir,
            debian_path,
            package,
            version)

        if not(os.path.exists(self.sources_path)):
            raise FileOrFolderNotFound("%s" % (self.path_to))

        self.sources_path_static = os.path.join(
            sources_static,
            debian_path,
            self.path_to)

    def is_dir(self):
        """ True if self is a directory, False if it's not """
        return os.path.isdir(self.sources_path)

    def is_file(self):
        """ True if sels is a file, False if it's not """
        return os.path.isfile(self.sources_path)

    def is_symlink(self):
        """ True if a folder/file is a symbolic link file, False if it's not
        """
        return os.path.islink(self.sources_path)

    def get_package(self):
        return self.package

    def get_version(self):
        return self.version

    def get_path(self):
        return self.path

    def get_deepest_element(self):
        if self.version == "":
            return self.package
        elif self.path == "":
            return self.version
        else:
            return self.path.split("/")[-1]

    def get_path_to(self):
        return self.path_to.rstrip("/")

    @staticmethod
    def get_stat(sources_path):
        """
        Returns the filetype and permissions of the folder/file
        on the disk, unix-styled.
        """
        # When porting to Python3, use stat.filemode directly
        sources_stat = os.lstat(sources_path)
        sources_mode, sources_size = sources_stat.st_mode, sources_stat.st_size
        perm_flags = [
            (stat.S_IRUSR, "r", "-"),
            (stat.S_IWUSR, "w", "-"),
            (stat.S_IXUSR, "x", "-"),
            (stat.S_IRGRP, "r", "-"),
            (stat.S_IWGRP, "w", "-"),
            (stat.S_IXGRP, "x", "-"),
            (stat.S_IROTH, "r", "-"),
            (stat.S_IWOTH, "w", "-"),
            (stat.S_IXOTH, "x", "-"),
            ]
        # XXX these flags should be enough.
        type_flags = [
            (stat.S_ISLNK, "l"),
            (stat.S_ISREG, "-"),
            (stat.S_ISDIR, "d"),
            ]
        # add the file type: d/l/-
        file_type = " "
        for ft, sign in type_flags:
            if ft(sources_mode):
                file_type = sign
                break
        file_perms = ""
        for (flag, do_true, do_false) in perm_flags:
            file_perms += do_true if (sources_mode & flag) else do_false

        file_size = sources_size

        symlink_dest = None
        if file_type == "l":
            symlink_dest = os.readlink(sources_path)

        return vars(LongFMT(file_type, file_perms, file_size, symlink_dest))

    @staticmethod
    def get_path_links(endpoint, path_to):
        """
        returns the path hierarchy with urls, to use with 'You are here:'
        [(name, url(name)), (...), ...]
        """
        path_dict = path_to.split('/')
        pathl = []

        # we import flask here, in order to permit the use of this module
        # without requiring the user to have flask (e.g. bin/debsources-update
        # can run in another machine without flask, because it doesn't use
        # this method)
        from flask import url_for

        for (i, p) in enumerate(path_dict):
            pathl.append((p, url_for(endpoint,
                                     path_to='/'.join(path_dict[:i+1]))))
        return pathl


class Directory(object):
    """ a folder in a package """

    def __init__(self, location, toplevel=False):
        # if the directory is a toplevel one, we remove the .pc folder
        self.sources_path = location.sources_path
        self.toplevel = toplevel
        self.location = location

    def get_listing(self):
        """
        returns the list of folders/files in a directory,
        along with their type (directory/file)
        in a tuple (name, type)
        """
        def get_type(f):
            if os.path.isdir(os.path.join(self.sources_path, f)):
                return "directory"
            else:
                return "file"
        get_stat, join_path = self.location.get_stat, os.path.join
        listing = sorted(dict(name=f, type=get_type(f),
                              stat=get_stat(join_path(self.sources_path, f)))
                         for f in os.listdir(self.sources_path))
        if self.toplevel:
            listing = filter(lambda x: x['name'] != ".pc", listing)

        return listing


class SourceFile(object):
    """ a source file in a package """

    def __init__(self, location):
        self.location = location
        self.sources_path = location.sources_path
        self.sources_path_static = location.sources_path_static
        self.mime = self._find_mime()

    def _find_mime(self):
        """ returns the mime encoding and type of a file """
        mime = magic.open(magic.MIME_TYPE)
        mime.load()
        type_ = mime.file(self.sources_path)
        mime.close()
        mime = magic.open(magic.MIME_ENCODING)
        mime.load()
        encoding = mime.file(self.sources_path)
        mime.close()
        return dict(encoding=encoding, type=type_)

    def get_mime(self):
        return self.mime

    def get_sha256sum(self, session):
        """
        Queries the DB and returns the shasum of the file.
        """
        shasum = session.query(Checksum.sha256) \
                        .filter(Checksum.package_id == Package.id) \
                        .filter(Package.name_id == PackageName.id) \
                        .filter(File.id == Checksum.file_id) \
                        .filter(PackageName.name == self.location.package) \
                        .filter(Package.version == self.location.version) \
                        .filter(File.path == str(self.location.path)) \
                        .first()
        # WARNING: in the DB path is binary, and here
        # location.path is unicode, because the path comes from
        # the URL. TODO: check with non-unicode paths
        if shasum:
            shasum = shasum[0]
        return shasum

    def istextfile(self):
        """True if self is a text file, False if it's not.

        """
        return filetype.is_text_file(self.mime['type'])
        # for substring in text_file_mimes:
        #     if substring in self.mime['type']:
        #         return True
        # return False

    def get_raw_url(self):
        """ return the raw url on disk (e.g. data/main/a/azerty/foo.bar) """
        return self.sources_path_static
