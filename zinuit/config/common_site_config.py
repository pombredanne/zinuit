import os, multiprocessing, getpass, json

try:
	from urllib.parse import urlparse
except ImportError:
	from urlparse import urlparse

default_config = {
	'restart_supervisor_on_update': False,
	'restart_systemd_on_update': False,
	'auto_update': False,
	'serve_default_site': True,
	'rebase_on_pull': False,
	'update_zinuit_on_update': True,
	'metel_user': getpass.getuser(),
	'shallow_clone': True,
	'background_workers': 1
}

def make_config(zinuit_path):
	make_pid_folder(zinuit_path)
	zinuit_config = get_config(zinuit_path)
	zinuit_config.update(default_config)
	zinuit_config.update(get_gunicorn_workers())
	update_config_for_metel(zinuit_config, zinuit_path)

	put_config(zinuit_config, zinuit_path)

def get_config(zinuit_path):
	return get_common_site_config(zinuit_path)

def get_common_site_config(zinuit_path):
	config_path = get_config_path(zinuit_path)
	if not os.path.exists(config_path):
		return {}
	with open(config_path, 'r') as f:
		return json.load(f)

def put_config(config, zinuit_path='.'):
	config_path = get_config_path(zinuit_path)
	with open(config_path, 'w') as f:
		return json.dump(config, f, indent=1, sort_keys=True)

def update_config(new_config, zinuit_path='.'):
	config = get_config(zinuit_path=zinuit_path)
	config.update(new_config)
	put_config(config, zinuit_path=zinuit_path)

def get_config_path(zinuit_path):
	return os.path.join(zinuit_path, 'sites', 'common_site_config.json')

def get_gunicorn_workers():
	'''This function will return the maximum workers that can be started depending upon
	number of cpu's present on the machine'''
	return {
		"gunicorn_workers": multiprocessing.cpu_count()
	}

def update_config_for_metel(config, zinuit_path):
	ports = make_ports(zinuit_path)

	for key in ('redis_cache', 'redis_queue', 'redis_socketio'):
		if key not in config:
			config[key] = "redis://localhost:{0}".format(ports[key])

	for key in ('webserver_port', 'socketio_port', 'file_watcher_port'):
		if key not in config:
			config[key] = ports[key]


	# TODO Optionally we need to add the host or domain name in case dns_multitenant is false

def make_ports(zinuit_path):
	zinuites_path = os.path.dirname(os.path.abspath(zinuit_path))

	default_ports = {
		"webserver_port": 8000,
		"socketio_port": 9000,
		"file_watcher_port": 6787,
		"redis_queue": 11000,
		"redis_socketio": 12000,
		"redis_cache": 13000
	}

	# collect all existing ports
	existing_ports = {}
	for folder in os.listdir(zinuites_path):
		zinuit_path = os.path.join(zinuites_path, folder)
		if os.path.isdir(zinuit_path):
			zinuit_config = get_config(zinuit_path)
			for key in list(default_ports.keys()):
				value = zinuit_config.get(key)

				# extract port from redis url
				if value and (key in ('redis_cache', 'redis_queue', 'redis_socketio')):
					value = urlparse(value).port

				if value:
					existing_ports.setdefault(key, []).append(value)

	# new port value = max of existing port value + 1
	ports = {}
	for key, value in list(default_ports.items()):
		existing_value = existing_ports.get(key, [])
		if existing_value:
			value = max(existing_value) + 1

		ports[key] = value

	return ports

def make_pid_folder(zinuit_path):
	pids_path = os.path.join(zinuit_path, 'config', 'pids')
	if not os.path.exists(pids_path):
		os.makedirs(pids_path)
