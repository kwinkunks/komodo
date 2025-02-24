from pkg_resources import DistributionNotFound, get_distribution

try:
    VERSION = get_distribution(__name__).version
except DistributionNotFound:
    try:
        from ._version import version as VERSION
    except ImportError:
        raise ImportError("Failed to find autogenerated _version.py.")
__version__ = VERSION
