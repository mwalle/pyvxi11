try:
    from version import __version__
except ImportError:
    __version__ = 'dev'

from vxi11 import Vxi11, Vxi11Error
