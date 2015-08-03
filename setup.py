from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages

extra = {}
try:
    from nowin_core.scripts import setup_cmd
    extra['cmdclass'] = {
        'initdb': setup_cmd.InitdbCommand,
        'shell': setup_cmd.ShellCommand
    }
except ImportError:
    pass

tests_require = [
    'mock',
    'pytest',
    'pytest-cov',
    'pytest-xdist',
    'pytest-capturelog',
    'pytest-mock',
]

setup(
    name='nowin_core',
    packages=find_packages(),
    install_requires=[
        'psutil',
        'SQLAlchemy',
        'zope.sqlalchemy',
        'transaction',
        'nose',
        'PyYaml',
        'Twisted',
        'zope.sqlalchemy',
    ],
    tests_require=[
        'nose-cov'
    ],
    extras_require=dict(
        tests=tests_require,
    ),
    **extra
)
