def getRevision(path=None):
    """Get revision by path

    """
    import os

    try:
        from mercurial import ui, hg
        from mercurial.error import RepoError
    except ImportError:
        import subprocess
        try:
            result = subprocess.check_output('hg id -n', cwd=path, shell=True)
        except subprocess.CalledProcessError:
            return
        else:
            return int(result.strip(' +\n'))
        return

    if path is None:
        path = os.curdir

    path = os.path.abspath(path)
    tail = True
    while tail:
        try:
            repo = hg.repository(ui.ui(), path)
        except RepoError:
            pass
        else:
            return repo['.'].rev()
        path, tail = os.path.split(path)
    return


def redirectTwistedLog():
    """transfer the twisted messages to the python logging system

    """
    import twisted.python.log
    observer = twisted.python.log.PythonLoggingObserver()
    observer.start()


def redirectException(logger=None, level=None):
    """Redirect uncaught exception to a logger

    """
    import sys
    import logging

    if logger is None:
        logger = logging.getLogger()
    if level is None:
        level = logging.ERROR

    def excepthook(*args):
        try:
            logger.log(level, 'Uncaught exception:', exc_info=args)
        except:
            logger.log(level,
                       'Encounter error when logging exception:',
                       sys.exc_info())
    sys.excepthook = excepthook


def decodeWin32Error(error):
    """Error message from win32 os is always not Unicode, here we detect what
    os we are using, and what encoding the os is using, decode message in
    error and return a new error instance with correct Unicode message

    """
    import os
    import locale
    import types
    if os.name != 'nt':
        return error
    _, encoding = locale.getdefaultlocale()
    new_args = []
    for item in error.args:
        if isinstance(item, types.StringType):
            new_args.append(item.decode(encoding))
        else:
            new_args.append(item)
    return error.__class__(*new_args)


def convertBpsToMbps(bytes_per_second):
    """Convert bytes per second to mbps (million bits per second)

    """
    bits = bytes_per_second * 8
    return bits / float(1000 * 1000)


def convertBpsToKbps(bytes_per_second):
    """Convert bytes per second to kbps (kilobits per second)

    """
    bits = bytes_per_second * 8
    return bits / float(1000)


def generateRandomCode():
    """Generate random code

    """
    import random
    import hashlib
    import datetime
    import os
    key = '%s%s%s' % (
        random.random(), datetime.datetime.now(), os.urandom(60))
    return unicode(hashlib.sha1(key).hexdigest())


def createTestingAccounts(
    session,
    count,
    name_pattern='test%s',
    email_pattern='test%s@now.in',
    password='testpass',
):
    """Creating many testing accounts

    """
    from nowin_core.models.user import UserModel
    user_model = UserModel(session)
    users = []
    for i in xrange(count):
        name = name_pattern % i
        email = email_pattern % i
        user = user_model.get_user_by_name(name)
        if user is not None:
            print 'user %s already exist, skip'
            continue
        user_id = user_model.create_user(user_name=name,
                                         email=email,
                                         display_name=name,
                                         password=password)
        user_model.activate_user(user_id, name, 'TW')
        users.append(user_id)
        session.flush()
        print 'create user', name
    session.commit()
    return users


def setKeepAlive(transport, idle=None, interval=None, probes=None):
    """Set the options of TCP keep alive to Twisted transport

    References to:
    http://tldp.org/HOWTO/TCP-Keepalive-HOWTO/overview.html

    Keep-alive for windows references to:
    http://bugs.python.org/issue6971

    @param idle: idle time before sending keepalive ACK ins seconds
    @param interval: interval of probe to send in seconds
    @param probes:  times of probe to send
    """
    import os
    import socket
    import logging
    logger = logging.getLogger(__name__)

    transport.setTcpKeepAlive(True)

    def setTcpOpt(opt, value):
        transport.socket.setsockopt(socket.SOL_TCP, opt, value)
    if os.name == 'nt':
        if idle or interval or probes:
            logger.warn("Python2.6 on Windows doesn't support "
                        "keepalive options, reference to "
                        "http://bugs.python.org/issue6971")
    else:
        if idle is not None:
            setTcpOpt(socket.TCP_KEEPIDLE, idle)
        if interval is not None:
            setTcpOpt(socket.TCP_KEEPINTVL, interval)
        if probes is not None:
            setTcpOpt(socket.TCP_KEEPCNT, probes)
