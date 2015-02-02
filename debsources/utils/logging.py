from __future__ import absolute_import

import logging


LOG_FMT_FILE = '%(asctime)s %(module)s:%(levelname)s %(message)s'
LOG_FMT_STDERR = '%(module)s:%(levelname)s %(message)s'
LOG_DATE_FMT = '%Y-%m-%d %H:%M:%S'

LOG_LEVELS = {  # XXX module logging has no built-in way to do this conversion
                # unless one uses the logging.config cannon. Really?!?
    'debug':    logging.DEBUG,    # verbosity >= 3
    'info':     logging.INFO,     # verbosity >= 2
    'warning':  logging.WARNING,  # verbosity >= 1
    'error':    logging.ERROR,    # verbosity >= 0
    'critical': logging.CRITICAL,
}
