from jinja2 import Environment, PackageLoader

__version__ = "4.1.0"

env = Environment(loader=PackageLoader('zinuit.config'))

METEL_VERSION = None

def set_metel_version(zinuit_path='.'):
	from .app import get_current_metel_version
	global METEL_VERSION
	if not METEL_VERSION:
		METEL_VERSION = get_current_metel_version(zinuit_path=zinuit_path)