import logging
import logging.handlers
from traceback import format_stack

from brotab.files import in_temp_dir


def _init_logger(tag, filename: str):
    FORMAT = '%(asctime)-15s %(process)-5d %(levelname)-8s %(filename)s:%(lineno)d:%(funcName)s %(message)s'
    MAX_LOG_SIZE = 50 * 1024 * 1024
    LOG_BACKUP_COUNT = 1

    log = logging.getLogger('brotab')
    log.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(
        filename=filename,
        maxBytes=MAX_LOG_SIZE,
        backupCount=LOG_BACKUP_COUNT,
    )
    handler.setFormatter(logging.Formatter(FORMAT))
    log.addHandler(handler)
    log.info('Logger has been created (%s)', tag)
    return log


def init_brotab_logger(tag: str):
    return _init_logger(tag, in_temp_dir('brotab.log'))


def init_mediator_logger(tag: str):
    return _init_logger(tag, in_temp_dir('brotab_mediator.log'))


def disable_logging():
    # disables flask request logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    log.disabled = True
    # TODO: investigate this, maybe we can redirect werkzeug from stdout to a file
    # log.handlers = []
    # disables my own logging in log_and_suppress_exceptions
    # app.logger.disabled = True
    # from flask.logging import default_handler
    # app.logger.removeHandler(default_handler)


def disable_click_echo():
    """Stupid flask started using click which unconditionally prints stupid
    messages"""

    def numb_echo(*args, **kwargs):
        pass

    import click
    click.echo = numb_echo
    click.secho = numb_echo


def stack():
    return '\n'.join(format_stack())


mediator_logger = init_mediator_logger('mediator')
brotab_logger = init_brotab_logger('brotab')
