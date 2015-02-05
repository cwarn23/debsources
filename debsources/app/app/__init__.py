# Copyright (C) 2013  Matthieu Caneill <matthieu.caneill@gmail.com>
#
# This file is part of Debsources.
#
# Debsources is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import importlib
import logging
from logging import Formatter, FileHandler, StreamHandler

from flask import Flask

from debsources.utils.conf import DebsConf
from debsources.utils.logging import LOG_LEVELS
from debsources.db import get_engine_session


class AppWrapper(object):
    """
    Contains an app and a session, and provides ways to drive all the init
    steps separately.
    """
    def __init__(self, config=None, session=None):
        """
        Creates a Flask application and sets up its configuration.
        If config and/or session are provided, they will overload the
        default behavior.
        """
        self.session = session
        self.app = Flask(__name__)

        if config is None:
            self.setup_conf()
        else:
            # config is a dict, or alike.
            self.app.config.update(config)

        self.ready()

    def ready(self):
        """
        Sets up SQLAlchemy, logging, and imports all the views.
        After creating an AppWrapper and calling this method, the app is ready.
        """
        if self.session is None:
            self.setup_sqlalchemy()
        # we load all the enabled blueprints
        self.setup_blueprints()

        self.setup_logging()

    def setup_conf(self):
        """
        Sets up the configuration, getting it from mainlib.
        """
        conf = DebsConf().parse_section("app")
        self.app.config.update(conf)

    def setup_sqlalchemy(self):
        """
        Creates an engine and a session for SQLAlchemy, using the database URI
        in the configuration.
        """
        db_uri = self.app.config["sqlalchemy_database_uri"]
        e, s = get_engine_session(db_uri,
                                  verbose=self.app.config["sqlalchemy_echo"])
        self.engine, self.session = e, s

    def setup_logging(self):
        """
        Sets up everything needed for logging.
        """
        fmt = Formatter('%(asctime)s %(levelname)s: %(message)s '
                        + '[in %(pathname)s:%(lineno)d]')
        log_level = logging.INFO
        try:
            log_level = LOG_LEVELS[self.app.config["log_level"]]
        except KeyError:  # might be raised by both "config" and "LOG_LEVELS",
            pass          # same treatment: fallback to default log_level

        stream_handler = StreamHandler()
        stream_handler.setFormatter(fmt)
        stream_handler.setLevel(log_level)
        self.app.logger.addHandler(stream_handler)

        if "LOG_FILE" in self.app.config:
            file_handler = FileHandler(self.app.config["log_file"])
            file_handler.setFormatter(fmt)
            file_handler.setLevel(log_level)
            self.app.logger.addHandler(file_handler)

    def setup_blueprints(self):
        bps = self.app.config['blueprints']
        for name, options in bps.iteritems():
            bp_module = importlib.import_module('debsources.app.'+name)
            bp = getattr(bp_module, 'bp_'+name)
            self.app.register_blueprint(
                bp,
                subdomain=options['subdomain'],
                )

    def run(self, *args, **kwargs):
        self.app.run(*args, **kwargs)


__all__ = ["AppWrapper"]
