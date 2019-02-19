import click
import sys, os, copy


@click.command('start')
@click.option('--no-dev', is_flag=True, default=False)
@click.option('--concurrency', '-c', type=str)
def start(no_dev, concurrency):
	"Start Metel development processes"
	from zinuit.utils import start
	start(no_dev=no_dev, concurrency=concurrency)


@click.command('restart')
@click.option('--web', is_flag=True, default=False)
@click.option('--supervisor', is_flag=True, default=False)
@click.option('--systemd', is_flag=True, default=False)
def restart(web, supervisor, systemd):
	"Restart supervisor processes or systemd units"
	from zinuit.utils import restart_supervisor_processes, restart_systemd_processes
	from zinuit.config.common_site_config import get_config
	if get_config('.').get('restart_supervisor_on_update') or supervisor:
		restart_supervisor_processes(zinuit_path='.', web_workers=web)
	if get_config('.').get('restart_systemd_on_update') or systemd:
		restart_systemd_processes(zinuit_path='.', web_workers=web)

@click.command('set-nginx-port')
@click.argument('site')
@click.argument('port', type=int)
def set_nginx_port(site, port):
	"Set nginx port for site"
	from zinuit.config.site_config import set_nginx_port
	set_nginx_port(site, port)


@click.command('set-ssl-certificate')
@click.argument('site')
@click.argument('ssl-certificate-path')
def set_ssl_certificate(site, ssl_certificate_path):
	"Set ssl certificate path for site"
	from zinuit.config.site_config import set_ssl_certificate
	set_ssl_certificate(site, ssl_certificate_path)


@click.command('set-ssl-key')
@click.argument('site')
@click.argument('ssl-certificate-key-path')
def set_ssl_certificate_key(site, ssl_certificate_key_path):
	"Set ssl certificate private key path for site"
	from zinuit.config.site_config import set_ssl_certificate_key
	set_ssl_certificate_key(site, ssl_certificate_key_path)


@click.command('set-url-root')
@click.argument('site')
@click.argument('url-root')
def set_url_root(site, url_root):
	"Set url root for site"
	from zinuit.config.site_config import set_url_root
	set_url_root(site, url_root)


@click.command('set-mariadb-host')
@click.argument('host')
def set_mariadb_host(host):
	"Set MariaDB host for zinuit"
	from zinuit.utils import set_mariadb_host
	set_mariadb_host(host)


@click.command('set-default-site')
@click.argument('site')
def set_default_site(site):
	"Set default site for zinuit"
	from zinuit.utils import set_default_site
	set_default_site(site)


@click.command('download-translations')
def download_translations():
	"Download latest translations"
	from zinuit.utils import download_translations_p
	download_translations_p()

@click.command('renew-lets-encrypt')
def renew_lets_encrypt():
	"Renew Let's Encrypt certificate"
	from zinuit.config.lets_encrypt import renew_certs
	renew_certs()

@click.command()
def shell(zinuit_path='.'):
	if not os.environ.get('SHELL'):
		print("Cannot get shell")
		sys.exit(1)
	if not os.path.exists('sites'):
		print("sites dir doesn't exist")
		sys.exit(1)
	env = copy.copy(os.environ)
	env['PS1'] = '(' + os.path.basename(os.path.dirname(os.path.abspath(__file__))) + ')' + env.get('PS1', '')
	env['PATH'] = os.path.dirname(os.path.abspath(os.path.join('env','bin')) + ':' + env['PATH'])
	os.chdir('sites')
	os.execve(env['SHELL'], [env['SHELL']], env)


@click.command('backup')
@click.argument('site')
def backup_site(site):
	"backup site"
	from zinuit.utils import get_sites, backup_site
	if not site in get_sites(zinuit_path='.'):
		print('site not found')
		sys.exit(1)
	backup_site(site, zinuit_path='.')


@click.command('backup-all-sites')
def backup_all_sites():
	"backup all sites"
	from zinuit.utils import backup_all_sites
	backup_all_sites(zinuit_path='.')


@click.command('release')
@click.argument('app')
@click.argument('bump-type', type=click.Choice(['major', 'minor', 'patch', 'stable', 'prerelease']))
@click.option('--from-branch', default='develop')
@click.option('--to-branch', default='master')
@click.option('--remote', default='upstream')
@click.option('--owner', default='metel')
@click.option('--repo-name')
@click.option('--dont-frontport', is_flag=True, default=False, help='Front port fixes to new branches, example merging hotfix(v10) into staging-fixes(v11)')
def release(app, bump_type, from_branch, to_branch, owner, repo_name, remote, dont_frontport):
	"Release app (internal to the Metel team)"
	from zinuit.release import release
	frontport = not dont_frontport
	release(zinuit_path='.', app=app, bump_type=bump_type, from_branch=from_branch, to_branch=to_branch,
		remote=remote, owner=owner, repo_name=repo_name, frontport=frontport)


@click.command('prepare-beta-release')
@click.argument('app')
@click.option('--owner', default='metel')
def prepare_beta_release(app, owner):
	"""Prepare major beta release from develop branch"""
	from zinuit.prepare_beta_release import prepare_beta_release
	prepare_beta_release(zinuit_path='.', app=app, owner=owner)


@click.command('disable-production')
def disable_production():
	"""Disables production environment for the zinuit."""
	from zinuit.config.production_setup import disable_production
	disable_production(zinuit_path='.')


@click.command('src')
def zinuit_src():
	"""Prints zinuit source folder path, which can be used as: cd `zinuit src` """
	import zinuit
	print(os.path.dirname(zinuit.__path__[0]))
