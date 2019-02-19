import click

import os, shutil
import os.path as osp
import logging

from datetime import datetime

from zinuit.utils import which, exec_cmd

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

def print_zinuit_version(ctx, param, value):
	"""Prints current zinuit version"""
	if not value or ctx.resilient_parsing:
		return

	import zinuit
	click.echo(zinuit.__version__)
	ctx.exit()

@click.group()
@click.option('--version', is_flag=True, is_eager=True, callback=print_zinuit_version, expose_value=False)
def zinuit_command(zinuit_path='.'):
	"""Zinuit manager for Metel"""
	import zinuit
	from zinuit.utils import setup_logging

	zinuit.set_metel_version(zinuit_path=zinuit_path)
	setup_logging(zinuit_path=zinuit_path)


from zinuit.commands.make import init, get_app, new_app, remove_app
zinuit_command.add_command(init)
zinuit_command.add_command(get_app)
zinuit_command.add_command(new_app)
zinuit_command.add_command(remove_app)


from zinuit.commands.update import update, retry_upgrade, switch_to_branch, switch_to_master, switch_to_develop
zinuit_command.add_command(update)
zinuit_command.add_command(retry_upgrade)
zinuit_command.add_command(switch_to_branch)
zinuit_command.add_command(switch_to_master)
zinuit_command.add_command(switch_to_develop)

from zinuit.commands.utils import (start, restart, set_nginx_port, set_ssl_certificate, set_ssl_certificate_key, set_url_root,
	set_mariadb_host, set_default_site, download_translations, shell, backup_site, backup_all_sites, release, renew_lets_encrypt,
	disable_production, zinuit_src, prepare_beta_release)
zinuit_command.add_command(start)
zinuit_command.add_command(restart)
zinuit_command.add_command(set_nginx_port)
zinuit_command.add_command(set_ssl_certificate)
zinuit_command.add_command(set_ssl_certificate_key)
zinuit_command.add_command(set_url_root)
zinuit_command.add_command(set_mariadb_host)
zinuit_command.add_command(set_default_site)
zinuit_command.add_command(download_translations)
zinuit_command.add_command(shell)
zinuit_command.add_command(backup_site)
zinuit_command.add_command(backup_all_sites)
zinuit_command.add_command(release)
zinuit_command.add_command(renew_lets_encrypt)
zinuit_command.add_command(disable_production)
zinuit_command.add_command(zinuit_src)
zinuit_command.add_command(prepare_beta_release)

from zinuit.commands.setup import setup
zinuit_command.add_command(setup)


from zinuit.commands.config import config
zinuit_command.add_command(config)

from zinuit.commands.git import remote_set_url, remote_reset_url, remote_urls
zinuit_command.add_command(remote_set_url)
zinuit_command.add_command(remote_reset_url)
zinuit_command.add_command(remote_urls)

from zinuit.commands.install import install
zinuit_command.add_command(install)

from zinuit.config.common_site_config import get_config
try:
	from urlparse 	  import urlparse
except ImportError:
	from urllib.parse import urlparse

@click.command('migrate-env')
@click.argument('python', type = str)
@click.option('--no-backup', default = False, help = 'Do not backup the existing Virtual Environment')
def migrate_env(python, no_backup = False):
	"""
	Migrate Virtual Environment to desired Python Version.
	"""
	try:
		# Clear Cache before Zinuit Dies.
		config = get_config(zinuit_path = os.getcwd())
		rredis = urlparse(config['redis_cache'])

		redis  = '{redis} -p {port}'.format(
			redis = which('redis-cli'),
			port  = rredis.port
		)

		log.debug('Clearing Redis Cache...')
		exec_cmd('{redis} FLUSHALL'.format(redis = redis))
		log.debug('Clearing Redis DataBase...')
		exec_cmd('{redis} FLUSHDB'.format(redis = redis))
	except Exception:
		log.warn('Please ensure Redis Connections are running or Daemonized.')

	try:
		# This is with the assumption that a zinuit is set-up within path.
		path       = os.getcwd()

		# I know, bad name for a flag. Thanks, Ameya! :| - <Administrator>
		if not no_backup:
			# Back, the f*ck up.
			parch = osp.join(path, 'archived_envs')
			if not osp.exists(parch):
				os.mkdir(parch)

			# Simply moving. Thanks, Ameya.
			# I'm keen to zip.
			source = osp.join(path, 'env')
			target = parch

			log.debug('Backing up Virtual Environment')
			stamp  = datetime.now().strftime('%Y%m%d_%H%M%S')
			dest   = osp.join(path, str(stamp))

			# WARNING: This is an archive, you might have to use virtualenv --relocate
			# That's because virtualenv creates symlinks with shebangs pointing to executables.
			# shebangs, shebangs - ricky martin.

			# ...and shutil.copytree is a f*cking mess.
			os.rename(source, dest)
			shutil.move(dest, target)

		log.debug('Setting up a New Virtual {python} Environment'.format(
			python = python
		))

		# Path to Python Executable (Basically $PYTHONPTH)
		python     = which(python)


		virtualenv = which('virtualenv')

		nvenv      = 'env'
		pvenv      = osp.join(path, nvenv)

		exec_cmd('{virtualenv} --python {python} {pvenv}'.format(
			virtualenv = virtualenv,
			python     = python,
			pvenv      = pvenv
		), cwd = path)

		pip = osp.join(pvenv, 'bin', 'pip')
		exec_cmd('{pip} install --upgrade pip'.format(pip=pip))
		exec_cmd('{pip} install --upgrade setuptools'.format(pip=pip))
		# TODO: Options

		papps  = osp.join(path, 'apps')
		apps   = ['metel', 'redapple'] + [app for app in os.listdir(papps) if app not in ['metel', 'redapple']]

		for app in apps:
			papp = osp.join(papps, app)
			if osp.isdir(papp) and osp.exists(osp.join(papp, 'setup.py')):
				exec_cmd('{pip} install -e {app}'.format(
					pip = pip, app = papp
				))

		log.debug('Migration Successful to {python}'.format(
			python = python
		))
	except:
		log.debug('Migration Error')
		raise

zinuit_command.add_command(migrate_env)

from zinuit.commands.make import exclude_app_for_update, include_app_for_update
zinuit_command.add_command(exclude_app_for_update)
zinuit_command.add_command(include_app_for_update)
