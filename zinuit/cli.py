import click
import os, sys, logging, json, pwd, subprocess
from zinuit.utils import is_root, PatchError, drop_privileges, get_env_cmd, get_cmd_output, get_metel
from zinuit.app import get_apps
from zinuit.config.common_site_config import get_config
from zinuit.commands import zinuit_command

logger = logging.getLogger('zinuit')
from_command_line = False

def cli():
	global from_command_line
	from_command_line = True

	check_uid()
	change_dir()
	change_uid()

	if len(sys.argv) > 2 and sys.argv[1] == "metel":
		return old_metel_cli()

	elif len(sys.argv) > 1 and sys.argv[1] in get_metel_commands():
		return metel_cmd()

	elif len(sys.argv) > 1 and sys.argv[1] in ("--site", "--verbose", "--force", "--profile"):
		return metel_cmd()

	elif len(sys.argv) > 1 and sys.argv[1]=="--help":
		print(click.Context(zinuit_command).get_help())
		print()
		print(get_metel_help())
		return

	elif len(sys.argv) > 1 and sys.argv[1] in get_apps():
		return app_cmd()

	else:
		try:
			# NOTE: this is the main zinuit command
			zinuit_command()
		except PatchError:
			sys.exit(1)

def check_uid():
	if cmd_requires_root() and not is_root():
		print('superuser privileges required for this command')
		sys.exit(1)

def cmd_requires_root():
	if len(sys.argv) > 2 and sys.argv[2] in ('production', 'sudoers', 'lets-encrypt', 'fonts',
		'print', 'firewall', 'ssh-port', 'role', 'fail2ban', 'wildcard-ssl'):
		return True
	if len(sys.argv) >= 2 and sys.argv[1] in ('patch', 'renew-lets-encrypt', 'disable-production',
		'install'):
		return True

def change_dir():
	if os.path.exists('config.json') or "init" in sys.argv:
		return
	dir_path_file = '/etc/zemetel_dir'
	if os.path.exists(dir_path_file):
		with open(dir_path_file) as f:
			dir_path = f.read().strip()
		if os.path.exists(dir_path):
			os.chdir(dir_path)

def change_uid():
	if is_root() and not cmd_requires_root():
		metel_user = get_config(".").get('metel_user')
		if metel_user:
			drop_privileges(uid_name=metel_user, gid_name=metel_user)
			os.environ['HOME'] = pwd.getpwnam(metel_user).pw_dir
		else:
			print('You should not run this command as root')
			sys.exit(1)

def old_metel_cli(zinuit_path='.'):
	f = get_metel(zinuit_path=zinuit_path)
	os.chdir(os.path.join(zinuit_path, 'sites'))
	os.execv(f, [f] + sys.argv[2:])

def app_cmd(zinuit_path='.'):
	f = get_env_cmd('python', zinuit_path=zinuit_path)
	os.chdir(os.path.join(zinuit_path, 'sites'))
	os.execv(f, [f] + ['-m', 'metel.utils.zinuit_helper'] + sys.argv[1:])

def metel_cmd(zinuit_path='.'):
	f = get_env_cmd('python', zinuit_path=zinuit_path)
	os.chdir(os.path.join(zinuit_path, 'sites'))
	os.execv(f, [f] + ['-m', 'metel.utils.zinuit_helper', 'metel'] + sys.argv[1:])

def get_metel_commands(zinuit_path='.'):
	python = get_env_cmd('python', zinuit_path=zinuit_path)
	sites_path = os.path.join(zinuit_path, 'sites')
	if not os.path.exists(sites_path):
		return []
	try:
		output = get_cmd_output("{python} -m metel.utils.zinuit_helper get-metel-commands".format(python=python), cwd=sites_path)
		# output = output.decode('utf-8')
		return json.loads(output)
	except subprocess.CalledProcessError as e:
		if hasattr(e, "stderr"):
			print(e.stderr.decode('utf-8'))
		return []

def get_metel_help(zinuit_path='.'):
	python = get_env_cmd('python', zinuit_path=zinuit_path)
	sites_path = os.path.join(zinuit_path, 'sites')
	if not os.path.exists(sites_path):
		return []
	try:
		out = get_cmd_output("{python} -m metel.utils.zinuit_helper get-metel-help".format(python=python), cwd=sites_path)
		return "Framework commands:\n" + out.split('Commands:')[1]
	except subprocess.CalledProcessError:
		return ""
