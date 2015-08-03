import logging.config
import os

import yaml
from twisted.application.service import Application

from nowin_core.server.services import StopOnErrorService
from nowin_core.utils import redirectException
from nowin_core.utils import redirectTwistedLog


def loadApp(name, ServiceCls):
    log_config_path = os.environ.get('NOWIN_LOG_CONFIG', 'logging.yaml')
    print 'Load log config:', log_config_path
    log_config = yaml.load(open(log_config_path, 'rt'))
    logging.config.dictConfig(log_config)

    logger = logging.getLogger()

    redirect_exc = bool(os.environ.get('NOWIN_REDIRECT_EXC', True))
    logger.info('Redirect exception: %s', redirect_exc)
    if redirect_exc:
        redirectException()

    redirect_tw_log = bool(os.environ.get('NOWIN_REDIRECT_TW_LOG', True))
    logger.info('Redirect Twisted logs: %s', redirect_tw_log)
    if redirect_tw_log:
        redirectTwistedLog()

    server_config_path = os.environ.get('NOWIN_SERVER_CONFIG', 'config.yaml')
    server_config = yaml.load(open(server_config_path, 'rt'))
    logger.info('Load server config: %s', server_config_path)
    application = Application(name)
    service = ServiceCls(server_config)
    stop_on_error = StopOnErrorService(service)
    stop_on_error.setServiceParent(application)
    return application
