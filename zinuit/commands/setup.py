from zinuit.utils import exec_cmd
import click, sys, json
import os

@click.group()
def setup():
	"Setup zinuit"
	pass

@click.command('sudoers')
@click.argument('user')
def setup_sudoers(user):
	"Add commands to sudoers list for execution without password"
	from zinuit.utils import setup_sudoers
	setup_sudoers(user)

@click.command('nginx')
@click.option('--yes', help='Yes to regeneration of nginx config file', default=False, is_flag=True)
def setup_nginx(yes=False):
	"generate config for nginx"
	from zinuit.config.nginx import make_nginx_conf
	make_nginx_conf(zinuit_path=".", yes=yes)

@click.command('reload-nginx')
def reload_nginx():
	from zinuit.config.production_setup import reload_nginx
	reload_nginx()

@click.command('supervisor')
@click.option('--user')
@click.option('--yes', help='Yes to regeneration of supervisor config', is_flag=True, default=False)
def setup_supervisor(user=None, yes=False):
	"generate config for supervisor with an optional user argument"
	from zinuit.config.supervisor import generate_supervisor_config
	generate_supervisor_config(zinuit_path=".", user=user, yes=yes)

@click.command('redis')
def setup_redis():
	"generate config for redis cache"
	from zinuit.config.redis import generate_config
	generate_config('.')


@click.command('fonts')
def setup_fonts():
	"Add metel fonts to system"
	from zinuit.utils import setup_fonts
	setup_fonts()

@click.command('production')
@click.argument('user')
@click.option('--yes', help='Yes to regeneration config', is_flag=True, default=False)
def setup_production(user, yes=False):
	"setup zinuit for production"
	from zinuit.config.production_setup import setup_production
	from zinuit.utils import run_playbook
	# Install prereqs for production
	from distutils.spawn import find_executable
	if not find_executable('ansible'):
		exec_cmd("sudo pip install ansible")
	if not find_executable('fail2ban-client'):
		exec_cmd("zinuit setup role fail2ban")
	if not find_executable('nginx'):
		exec_cmd("zinuit setup role nginx")
	if not find_executable('supervisord'):
		exec_cmd("zinuit setup role supervisor")
	setup_production(user=user, yes=yes)


@click.command('auto-update')
def setup_auto_update():
	"Add cronjob for zinuit auto update"
	from zinuit.utils import setup_auto_update
	setup_auto_update()


@click.command('backups')
def setup_backups():
	"Add cronjob for zinuit backups"
	from zinuit.utils import setup_backups
	setup_backups()

@click.command('env')
@click.option('--python', type = str, default = 'python', help = 'Path to Python Executable.')
def setup_env(python='python'):
	"Setup virtualenv for zinuit"
	from zinuit.utils import setup_env
	setup_env(python=python)

@click.command('firewall')
@click.option('--ssh_port')
@click.option('--force')
def setup_firewall(ssh_port=None, force=False):
	"Setup firewall"
	from zinuit.utils import run_playbook

	if not force:
		click.confirm('Setting up the firewall will block all ports except 80, 443 and 22\n'
			'Do you want to continue?',
			abort=True)

	if not ssh_port:
		ssh_port = 22

	run_playbook('roles/zinuit/tasks/setup_firewall.yml', {"ssh_port": ssh_port})

@click.command('ssh-port')
@click.argument('port')
@click.option('--force')
def set_ssh_port(port, force=False):
	"Set SSH Port"
	from zinuit.utils import run_playbook

	if not force:
		click.confirm('This will change your SSH Port to {}\n'
			'Do you want to continue?'.format(port),
			abort=True)

	run_playbook('roles/zinuit/tasks/change_ssh_port.yml', {"ssh_port": port})

@click.command('lets-encrypt')
@click.argument('site')
@click.option('--custom-domain')
@click.option('-n', '--non-interactive', default=False, is_flag=True, help="Run certbot non-interactively. Shouldn't be used on 1'st attempt")
def setup_letsencrypt(site, custom_domain, non_interactive):
	"Setup lets-encrypt for site"
	from zinuit.config.lets_encrypt import setup_letsencrypt
	setup_letsencrypt(site, custom_domain, zinuit_path='.', interactive=not non_interactive)


@click.command('wildcard-ssl')
@click.argument('domain')
@click.option('--email')
@click.option('--exclude-base-domain', default=False, is_flag=True, help="SSL Certificate not applicable for base domain")
def setup_wildcard_ssl(domain, email, exclude_base_domain):
	''' Setup wildcard ssl certificate '''
	from zinuit.config.lets_encrypt import setup_wildcard_ssl
	setup_wildcard_ssl(domain, email, zinuit_path='.', exclude_base_domain=exclude_base_domain)


@click.command('procfile')
def setup_procfile():
	"Setup Procfile for zinuit start"
	from zinuit.config.procfile import setup_procfile
	setup_procfile('.')


@click.command('socketio')
def setup_socketio():
	"Setup node deps for socketio server"
	from zinuit.utils import setup_socketio
	setup_socketio()

@click.command('requirements', help="Update Python and Node packages")
@click.option('--node', help="Update only Node packages", default=False, is_flag=True)
@click.option('--python', help="Update only Python packages", default=False, is_flag=True)
def setup_requirements(node=False, python=False):
	"Setup python and node requirements"

	if not node:
		setup_python_requirements()
	if not python:
		setup_node_requirements()

def setup_python_requirements():
	from zinuit.utils import update_requirements
	update_requirements()

def setup_node_requirements():
	from zinuit.utils import update_node_packages
	update_node_packages()


@click.command('manager')
@click.option('--yes', help='Yes to regeneration of nginx config file', default=False, is_flag=True)
@click.option('--port', help='Port on which you want to run zinmanager', default=23624)
@click.option('--domain', help='Domain on which you want to run zinmanager')
def setup_manager(yes=False, port=23624, domain=None):
	"Setup zinuit-manager.local site with the zinmanager app installed on it"
	from six.moves import input
	create_new_site = True
	if 'zinuit-manager.local' in os.listdir('sites'):
		ans = input('Site already exists. Overwrite existing site? [Y/n]: ').lower()
		while ans not in ('y', 'n', ''):
			ans = input(
				'Please enter "y" or "n". Site already exists. Overwrite existing site? [Y/n]: ').lower()
		if ans == 'n':
			create_new_site = False
	if create_new_site:
		exec_cmd("zinuit new-site --force zinuit-manager.local")

	if 'zinmanager' in os.listdir('apps'):
		print('App already exists. Skipping app download.')
	else: 
		exec_cmd("zinuit get-app zinmanager")

	exec_cmd("zinuit --site zinuit-manager.local install-app zinmanager")

	from zinuit.config.common_site_config import get_config
	zinuit_path = '.'
	conf = get_config(zinuit_path)
	if conf.get('restart_supervisor_on_update') or conf.get('restart_systemd_on_update'):
		# implicates a production setup or so I presume
		if not domain:
			print("Please specify the site name on which you want to host zinuit-manager using the 'domain' flag")
			sys.exit(1)

		from zinuit.utils import get_sites, get_zinuit_name
		zinuit_name = get_zinuit_name(zinuit_path)

		if domain not in get_sites(zinuit_path):
			raise Exception("No such site")

		from zinuit.config.nginx import make_zinmanager_nginx_conf
		make_zinmanager_nginx_conf(zinuit_path, yes=yes, port=port, domain=domain)


@click.command('config')
def setup_config():
	"overwrite or make config.json"
	from zinuit.config.common_site_config import make_config
	make_config('.')


@click.command('add-domain')
@click.argument('domain')
@click.option('--site', prompt=True)
@click.option('--ssl-certificate', help="Absolute path to SSL Certificate")
@click.option('--ssl-certificate-key', help="Absolute path to SSL Certificate Key")
def add_domain(domain, site=None, ssl_certificate=None, ssl_certificate_key=None):
	"""Add custom domain to site"""
	from zinuit.config.site_config import add_domain

	if not site:
		print("Please specify site")
		sys.exit(1)

	add_domain(site, domain, ssl_certificate, ssl_certificate_key, zinuit_path='.')

@click.command('remove-domain')
@click.argument('domain')
@click.option('--site', prompt=True)
def remove_domain(domain, site=None):
	"""Remove custom domain from a site"""
	from zinuit.config.site_config import remove_domain

	if not site:
		print("Please specify site")
		sys.exit(1)

	remove_domain(site, domain, zinuit_path='.')

@click.command('sync-domains')
@click.option('--domain', multiple=True)
@click.option('--site', prompt=True)
def sync_domains(domain=None, site=None):
	from zinuit.config.site_config import sync_domains

	if not site:
		print("Please specify site")
		sys.exit(1)

	try:
		domains = list(map(str,domain))
	except Exception:
		print("Domains should be a json list of strings or dictionaries")
		sys.exit(1)

	changed = sync_domains(site, domains, zinuit_path='.')

	# if changed, success, else failure
	sys.exit(0 if changed else 1)

@click.command('role')
@click.argument('role')
@click.option('--admin_emails', default='')
@click.option('--mysql_root_password')
def setup_roles(role, **kwargs):
	"Install dependancies via roles"
	from zinuit.utils import run_playbook

	extra_vars = {"production": True}
	extra_vars.update(kwargs)

	if role:
		run_playbook('site.yml', extra_vars=extra_vars, tag=role)
	else:
		run_playbook('site.yml', extra_vars=extra_vars)

@click.command('fail2ban')
@click.option('--maxretry', default=6, help="Number of matches (i.e. value of the counter) which triggers ban action on the IP. Default is 6 seconds" )
@click.option('--bantime', default=600, help="The counter is set to zero if no match is found within 'findtime' seconds. Default is 600 seconds")
@click.option('--findtime', default=600, help='Duration (in seconds) for IP to be banned for. Negative number for "permanent" ban. Default is 600 seconds')
def setup_nginx_proxy_jail(**kwargs):
	from zinuit.utils import run_playbook
	run_playbook('roles/fail2ban/tasks/configure_nginx_jail.yml', extra_vars=kwargs)

@click.command('systemd')
@click.option('--user')
@click.option('--yes', help='Yes to regeneration of systemd config files', is_flag=True, default=False)
@click.option('--stop', help='Stop zinuit services', is_flag=True, default=False)
@click.option('--create-symlinks', help='Create Symlinks', is_flag=True, default=False)
@click.option('--delete-symlinks', help='Delete Symlinks', is_flag=True, default=False)
def setup_systemd(user=None, yes=False, stop=False, create_symlinks=False, delete_symlinks=False):
	"generate configs for systemd with an optional user argument"
	from zinuit.config.systemd import generate_systemd_config
	generate_systemd_config(zinuit_path=".", user=user, yes=yes,
		stop=stop, create_symlinks=create_symlinks, delete_symlinks=delete_symlinks)

setup.add_command(setup_sudoers)
setup.add_command(setup_nginx)
setup.add_command(reload_nginx)
setup.add_command(setup_supervisor)
setup.add_command(setup_redis)
setup.add_command(setup_letsencrypt)
setup.add_command(setup_wildcard_ssl)
setup.add_command(setup_production)
setup.add_command(setup_auto_update)
setup.add_command(setup_backups)
setup.add_command(setup_env)
setup.add_command(setup_procfile)
setup.add_command(setup_socketio)
setup.add_command(setup_requirements)
setup.add_command(setup_manager)
setup.add_command(setup_config)
setup.add_command(setup_fonts)
setup.add_command(add_domain)
setup.add_command(remove_domain)
setup.add_command(sync_domains)
setup.add_command(setup_firewall)
setup.add_command(set_ssh_port)
setup.add_command(setup_roles)
setup.add_command(setup_nginx_proxy_jail)
setup.add_command(setup_systemd)
