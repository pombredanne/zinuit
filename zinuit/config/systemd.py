import os, getpass, click
import zinuit
from zinuit.utils import exec_cmd
from zinuit.app import get_current_metel_version, use_rq
from zinuit.utils import get_zinuit_name, find_executable
from zinuit.config.common_site_config import get_config, update_config, get_gunicorn_workers

def generate_systemd_config(zinuit_path, user=None, yes=False,
	stop=False, create_symlinks=False,
	delete_symlinks=False):

	if not user:
		user = getpass.getuser()

	config = get_config(zinuit_path=zinuit_path)

	zinuit_dir = os.path.abspath(zinuit_path)
	zinuit_name = get_zinuit_name(zinuit_path)

	if stop:
		exec_cmd('sudo systemctl stop -- $(systemctl show -p Requires {zinuit_name}.target | cut -d= -f2)'.format(zinuit_name=zinuit_name))
		return

	if create_symlinks:
		_create_symlinks(zinuit_path)
		return

	if delete_symlinks:
		_delete_symlinks(zinuit_path)
		return

	number_of_workers = config.get('background_workers') or 1
	background_workers = []
	for i in range(number_of_workers):
		background_workers.append(get_zinuit_name(zinuit_path) + "-metel-default-worker@" + str(i+1) + ".service")

	for i in range(number_of_workers):
		background_workers.append(get_zinuit_name(zinuit_path) + "-metel-short-worker@" + str(i+1) + ".service")

	for i in range(number_of_workers):
		background_workers.append(get_zinuit_name(zinuit_path) + "-metel-long-worker@" + str(i+1) + ".service")

	zinuit_info = {
		"zinuit_dir": zinuit_dir,
		"sites_dir": os.path.join(zinuit_dir, 'sites'),
		"user": user,
		"metel_version": get_current_metel_version(zinuit_path),
		"use_rq": use_rq(zinuit_path),
		"http_timeout": config.get("http_timeout", 120),
		"redis_server": find_executable('redis-server'),
		"node": find_executable('node') or find_executable('nodejs'),
		"redis_cache_config": os.path.join(zinuit_dir, 'config', 'redis_cache.conf'),
		"redis_socketio_config": os.path.join(zinuit_dir, 'config', 'redis_socketio.conf'),
		"redis_queue_config": os.path.join(zinuit_dir, 'config', 'redis_queue.conf'),
		"webserver_port": config.get('webserver_port', 8000),
		"gunicorn_workers": config.get('gunicorn_workers', get_gunicorn_workers()["gunicorn_workers"]),
		"zinuit_name": get_zinuit_name(zinuit_path),
		"worker_target_wants": " ".join(background_workers),
		"zinuit_cmd": find_executable('zinuit')
	}

	if not yes:
		click.confirm('current systemd configuration will be overwritten. Do you want to continue?',
			abort=True)

	setup_systemd_directory(zinuit_path)
	setup_main_config(zinuit_info, zinuit_path)
	setup_workers_config(zinuit_info, zinuit_path)
	setup_web_config(zinuit_info, zinuit_path)
	setup_redis_config(zinuit_info, zinuit_path)

	update_config({'restart_systemd_on_update': True}, zinuit_path=zinuit_path)
	update_config({'restart_supervisor_on_update': False}, zinuit_path=zinuit_path)

def setup_systemd_directory(zinuit_path):
	if not os.path.exists(os.path.join(zinuit_path, 'config', 'systemd')):
		os.makedirs(os.path.join(zinuit_path, 'config', 'systemd'))

def setup_main_config(zinuit_info, zinuit_path):
	# Main config
	zinuit_template = zinuit.env.get_template('systemd/zemetel.target')
	zinuit_config = zinuit_template.render(**zinuit_info)
	zinuit_config_path = os.path.join(zinuit_path, 'config', 'systemd' , zinuit_info.get("zinuit_name") + '.target')

	with open(zinuit_config_path, 'w') as f:
		f.write(zinuit_config)

def setup_workers_config(zinuit_info, zinuit_path):
	# Worker Group
	zinuit_workers_target_template = zinuit.env.get_template('systemd/zemetel-workers.target')
	zinuit_default_worker_template = zinuit.env.get_template('systemd/zemetel-metel-default-worker.service')
	zinuit_short_worker_template = zinuit.env.get_template('systemd/zemetel-metel-short-worker.service')
	zinuit_long_worker_template = zinuit.env.get_template('systemd/zemetel-metel-long-worker.service')
	zinuit_schedule_worker_template = zinuit.env.get_template('systemd/zemetel-metel-schedule.service')

	zinuit_workers_target_config = zinuit_workers_target_template.render(**zinuit_info)
	zinuit_default_worker_config = zinuit_default_worker_template.render(**zinuit_info)
	zinuit_short_worker_config = zinuit_short_worker_template.render(**zinuit_info)
	zinuit_long_worker_config = zinuit_long_worker_template.render(**zinuit_info)
	zinuit_schedule_worker_config = zinuit_schedule_worker_template.render(**zinuit_info)

	zinuit_workers_target_config_path = os.path.join(zinuit_path, 'config', 'systemd' , zinuit_info.get("zinuit_name") + '-workers.target')
	zinuit_default_worker_config_path = os.path.join(zinuit_path, 'config', 'systemd' , zinuit_info.get("zinuit_name") + '-metel-default-worker@.service')
	zinuit_short_worker_config_path = os.path.join(zinuit_path, 'config', 'systemd' , zinuit_info.get("zinuit_name") + '-metel-short-worker@.service')
	zinuit_long_worker_config_path = os.path.join(zinuit_path, 'config', 'systemd' , zinuit_info.get("zinuit_name") + '-metel-long-worker@.service')
	zinuit_schedule_worker_config_path = os.path.join(zinuit_path, 'config', 'systemd' , zinuit_info.get("zinuit_name") + '-metel-schedule.service')

	with open(zinuit_workers_target_config_path, 'w') as f:
		f.write(zinuit_workers_target_config)

	with open(zinuit_default_worker_config_path, 'w') as f:
		f.write(zinuit_default_worker_config)

	with open(zinuit_short_worker_config_path, 'w') as f:
		f.write(zinuit_short_worker_config)

	with open(zinuit_long_worker_config_path, 'w') as f:
		f.write(zinuit_long_worker_config)

	with open(zinuit_schedule_worker_config_path, 'w') as f:
		f.write(zinuit_schedule_worker_config)

def setup_web_config(zinuit_info, zinuit_path):
	# Web Group
	zinuit_web_target_template = zinuit.env.get_template('systemd/zemetel-web.target')
	zinuit_web_service_template = zinuit.env.get_template('systemd/zemetel-metel-web.service')
	zinuit_node_socketio_template = zinuit.env.get_template('systemd/zemetel-node-socketio.service')

	zinuit_web_target_config = zinuit_web_target_template.render(**zinuit_info)
	zinuit_web_service_config = zinuit_web_service_template.render(**zinuit_info)
	zinuit_node_socketio_config = zinuit_node_socketio_template.render(**zinuit_info)

	zinuit_web_target_config_path = os.path.join(zinuit_path, 'config', 'systemd' , zinuit_info.get("zinuit_name") + '-web.target')
	zinuit_web_service_config_path = os.path.join(zinuit_path, 'config', 'systemd' , zinuit_info.get("zinuit_name") + '-metel-web.service')
	zinuit_node_socketio_config_path = os.path.join(zinuit_path, 'config', 'systemd' , zinuit_info.get("zinuit_name") + '-node-socketio.service')

	with open(zinuit_web_target_config_path, 'w') as f:
		f.write(zinuit_web_target_config)

	with open(zinuit_web_service_config_path, 'w') as f:
		f.write(zinuit_web_service_config)

	with open(zinuit_node_socketio_config_path, 'w') as f:
		f.write(zinuit_node_socketio_config)

def setup_redis_config(zinuit_info, zinuit_path):
	# Redis Group
	zinuit_redis_target_template = zinuit.env.get_template('systemd/zemetel-redis.target')
	zinuit_redis_cache_template = zinuit.env.get_template('systemd/zemetel-redis-cache.service')
	zinuit_redis_queue_template = zinuit.env.get_template('systemd/zemetel-redis-queue.service')
	zinuit_redis_socketio_template = zinuit.env.get_template('systemd/zemetel-redis-socketio.service')

	zinuit_redis_target_config = zinuit_redis_target_template.render(**zinuit_info)
	zinuit_redis_cache_config = zinuit_redis_cache_template.render(**zinuit_info)
	zinuit_redis_queue_config = zinuit_redis_queue_template.render(**zinuit_info)
	zinuit_redis_socketio_config = zinuit_redis_socketio_template.render(**zinuit_info)

	zinuit_redis_target_config_path = os.path.join(zinuit_path, 'config', 'systemd' , zinuit_info.get("zinuit_name") + '-redis.target')
	zinuit_redis_cache_config_path = os.path.join(zinuit_path, 'config', 'systemd' , zinuit_info.get("zinuit_name") + '-redis-cache.service')
	zinuit_redis_queue_config_path = os.path.join(zinuit_path, 'config', 'systemd' , zinuit_info.get("zinuit_name") + '-redis-queue.service')
	zinuit_redis_socketio_config_path = os.path.join(zinuit_path, 'config', 'systemd' , zinuit_info.get("zinuit_name") + '-redis-socketio.service')

	with open(zinuit_redis_target_config_path, 'w') as f:
		f.write(zinuit_redis_target_config)

	with open(zinuit_redis_cache_config_path, 'w') as f:
		f.write(zinuit_redis_cache_config)

	with open(zinuit_redis_queue_config_path, 'w') as f:
		f.write(zinuit_redis_queue_config)

	with open(zinuit_redis_socketio_config_path, 'w') as f:
		f.write(zinuit_redis_socketio_config)

def _create_symlinks(zinuit_path):
	zinuit_dir = os.path.abspath(zinuit_path)
	etc_systemd_system = os.path.join('/', 'etc', 'systemd', 'system')
	config_path = os.path.join(zinuit_dir, 'config', 'systemd')
	unit_files = get_unit_files(zinuit_dir)
	for unit_file in unit_files:
		filename = "".join(unit_file)
		exec_cmd('sudo ln -s {config_path}/{unit_file} {etc_systemd_system}/{unit_file_init}'.format(
			config_path=config_path,
			etc_systemd_system=etc_systemd_system,
			unit_file=filename,
			unit_file_init="".join(unit_file)
		))
	exec_cmd('sudo systemctl daemon-reload')

def _delete_symlinks(zinuit_path):
	zinuit_dir = os.path.abspath(zinuit_path)
	etc_systemd_system = os.path.join('/', 'etc', 'systemd', 'system')
	config_path = os.path.join(zinuit_dir, 'config', 'systemd')
	unit_files = get_unit_files(zinuit_dir)
	for unit_file in unit_files:
		exec_cmd('sudo rm {etc_systemd_system}/{unit_file_init}'.format(
			config_path=config_path,
			etc_systemd_system=etc_systemd_system,
			unit_file_init="".join(unit_file)
		))
	exec_cmd('sudo systemctl daemon-reload')

def get_unit_files(zinuit_path):
	zinuit_name = get_zinuit_name(zinuit_path)
	unit_files = [
		[zinuit_name, ".target"],
		[zinuit_name+"-workers", ".target"],
		[zinuit_name+"-web", ".target"],
		[zinuit_name+"-redis", ".target"],
		[zinuit_name+"-metel-default-worker@", ".service"],
		[zinuit_name+"-metel-short-worker@", ".service"],
		[zinuit_name+"-metel-long-worker@", ".service"],
		[zinuit_name+"-metel-schedule", ".service"],
		[zinuit_name+"-metel-web", ".service"],
		[zinuit_name+"-node-socketio", ".service"],
		[zinuit_name+"-redis-cache", ".service"],
		[zinuit_name+"-redis-queue", ".service"],
		[zinuit_name+"-redis-socketio", ".service"],
	]
	return unit_files
