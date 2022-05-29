from os import environ
from os.path import exists
from os.path import expanduser

from brotab.files import slurp_lines
from brotab.mediator.const import DEFAULT_HTTP_IFACE
from brotab.mediator.const import DEFAULT_MAX_HTTP_PORT
from brotab.mediator.const import DEFAULT_MIN_HTTP_PORT
from brotab.mediator.log import mediator_logger

CONFIG = environ.get('XDG_CONFIG_HOME', expanduser('~/.config'))
DEFAULT_FILENAME = '{0}/brotab/brotab.env'.format(CONFIG)


def http_iface():
    return environ.get('HTTP_IFACE', DEFAULT_HTTP_IFACE)


def min_http_port():
    return environ.get('MIN_HTTP_PORT', DEFAULT_MIN_HTTP_PORT)


def max_http_port():
    return environ.get('MAX_HTTP_PORT', DEFAULT_MAX_HTTP_PORT)


def load_dotenv(filename=None):
    if filename is None: filename = DEFAULT_FILENAME
    mediator_logger.info('Loading .env file: %s', filename)
    if not exists(filename):
        mediator_logger.info('No .env file found: %s', filename)
        return
    for line in slurp_lines(filename):
        if not line or line.startswith('#'): continue
        key, value = line.split('=', 1)
        environ[key] = value
