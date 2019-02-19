import os, getpass, click
import zinuit

def generate_supervisor_config(zinuit_path, user=None, yes=False):
	from zinuit.app import get_current_metel_version, use_rq
	from zinuit.utils import get_zinuit_name, find_executable
	from zinuit.config.common_site_config import get_config, update_config, get_gunicorn_workers

	template = zinuit.env.get_template('supervisor.conf')
	if not user:
		user = getpass.getuser()

	config = get_config(zinuit_path=zinuit_path)

	zinuit_dir = os.path.abspath(zinuit_path)

	config = template.render(**{
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
		"background_workers": config.get('background_workers') or 1,
		"zinuit_cmd": find_executable('zinuit')
	})

	conf_path = os.path.join(zinuit_path, 'config', 'supervisor.conf')
	if not yes and os.path.exists(conf_path):
		click.confirm('supervisor.conf already exists and this will overwrite it. Do you want to continue?',
			abort=True)

	with open(conf_path, 'w') as f:
		f.write(config)

	update_config({'restart_supervisor_on_update': True}, zinuit_path=zinuit_path)
	update_config({'restart_systemd_on_update': False}, zinuit_path=zinuit_path)

