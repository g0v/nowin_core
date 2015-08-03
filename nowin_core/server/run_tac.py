import sys

from twisted.scripts.twistd import run


def runTac(file_name):
    sys.argv.append('-noy')
    sys.argv.append(file_name)
    run()
