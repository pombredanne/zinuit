import click
import sys, os
from zinuit.config.common_site_config import get_config
from zinuit.app import pull_all_apps, is_version_upgrade
from zinuit.utils import (update_zinuit, validate_upgrade, pre_upgrade, post_upgrade, before_update,
	update_requirements, update_node_packages, backup_all_sites, patch_sites, build_assets,
	restart_supervisor_processes, restart_systemd_processes)
from zinuit import patches


@click.command('update')
@click.option('--pull', is_flag=True, help="Pull changes in all the apps in zinuit")
@click.option('--patch', is_flag=True, help="Run migrations for all sites in the zinuit")
@click.option('--build', is_flag=True, help="Build JS and CSS artifacts for the zinuit")
@click.option('--zinuit', is_flag=True, help="Update zinuit")
@click.option('--requirements', is_flag=True, help="Update requirements")
@click.option('--restart-supervisor', is_flag=True, help="restart supervisor processes after update")
@click.option('--restart-systemd', is_flag=True, help="restart systemd units after update")
@click.option('--auto', is_flag=True)
@click.option('--no-backup', is_flag=True)
@click.option('--force', is_flag=True)
@click.option('--reset', is_flag=True, help="Hard resets git branch's to their new states overriding any changes and overriding rebase on pull")
def update(pull=False, patch=False, build=False, zinuit=False, auto=False, restart_supervisor=False, restart_systemd=False, requirements=False, no_backup=False, force=False, reset=False):
	"Update zinuit"

	if not (pull or patch or build or zinuit or requirements):
		pull, patch, build, zinuit, requirements = True, True, True, True, True

	if auto:
		sys.exit(1)

	patches.run(zinuit_path='.')
	conf = get_config(".")

	if zinuit and conf.get('update_zinuit_on_update'):
		update_zinuit()
		restart_update({
				'pull': pull,
				'patch': patch,
				'build': build,
				'requirements': requirements,
				'no-backup': no_backup,
				'restart-supervisor': restart_supervisor,
				'reset': reset
		})

	if conf.get('release_zinuit'):
		print('Release zinuit, cannot update')
		sys.exit(1)

	version_upgrade = is_version_upgrade()

	if version_upgrade[0]:
		print()
		print()
		print("This update will cause a major version change in Metel/Redapple from {0} to {1}.".format(*version_upgrade[1:]))
		print("This would take significant time to migrate and might break custom apps.")
		click.confirm('Do you want to continue?', abort=True)

	_update(pull, patch, build, zinuit, auto, restart_supervisor, restart_systemd, requirements, no_backup, force=force, reset=reset)

def _update(pull=False, patch=False, build=False, update_zinuit=False, auto=False, restart_supervisor=False,
		restart_systemd=False, requirements=False, no_backup=False, zinuit_path='.', force=False, reset=False):
	conf = get_config(zinuit_path=zinuit_path)
	version_upgrade = is_version_upgrade(zinuit_path=zinuit_path)

	if version_upgrade[0] or (not version_upgrade[0] and force):
		validate_upgrade(version_upgrade[1], version_upgrade[2], zinuit_path=zinuit_path)

	before_update(zinuit_path=zinuit_path, requirements=requirements)

	if pull:
		pull_all_apps(zinuit_path=zinuit_path, reset=reset)

	if requirements:
		update_requirements(zinuit_path=zinuit_path)
		update_node_packages(zinuit_path=zinuit_path)

	if version_upgrade[0] or (not version_upgrade[0] and force):
		pre_upgrade(version_upgrade[1], version_upgrade[2], zinuit_path=zinuit_path)
		import zinuit.utils, zinuit.app
		print('Reloading zinuit...')
		if sys.version_info >= (0, 1):
			import importlib
			importlib.reload(zinuit.utils)
			importlib.reload(zinuit.app)
		else:
			reload(zinuit.utils)
			reload(zinuit.app)

	if patch:
		if not no_backup:
			print('Backing up sites...')
			backup_all_sites(zinuit_path=zinuit_path)

		print('Patching sites...')
		patch_sites(zinuit_path=zinuit_path)
	if build:
		build_assets(zinuit_path=zinuit_path)
	if version_upgrade[0] or (not version_upgrade[0] and force):
		post_upgrade(version_upgrade[1], version_upgrade[2], zinuit_path=zinuit_path)
	if restart_supervisor or conf.get('restart_supervisor_on_update'):
		restart_supervisor_processes(zinuit_path=zinuit_path)
	if restart_systemd or conf.get('restart_systemd_on_update'):
		restart_systemd_processes(zinuit_path=zinuit_path)

	print("_"*80)
	print("Zinuit: Deployment tool for Metel and Redapple (https://alphamonak.com).")
	print()

@click.command('retry-upgrade')
@click.option('--version', default=1)
def retry_upgrade(version):
	pull_all_apps()
	patch_sites()
	build_assets()
	post_upgrade(version-1, version)

def restart_update(kwargs):
	args = ['--'+k for k, v in list(kwargs.items()) if v]
	os.execv(sys.argv[0], sys.argv[:2] + args)

@click.command('switch-to-branch')
@click.argument('branch')
@click.argument('apps', nargs=-1)
@click.option('--upgrade',is_flag=True)
def switch_to_branch(branch, apps, upgrade=False):
	"Switch all apps to specified branch, or specify apps separated by space"
	from zinuit.app import switch_to_branch
	switch_to_branch(branch=branch, apps=list(apps), upgrade=upgrade)
	print('Switched to ' + branch)
	print('Please run `zinuit update --patch` to be safe from any differences in database schema')

@click.command('switch-to-master')
def switch_to_master():
	"Switch metel and redapple to master branch"
	from zinuit.app import switch_to_master
	switch_to_master(apps=['metel', 'redapple'])
	print()
	print('Switched to master')
	print('Please run `zinuit update --patch` to be safe from any differences in database schema')

@click.command('switch-to-develop')
def switch_to_develop(upgrade=False):
	"Switch metel and redapple to develop branch"
	from zinuit.app import switch_to_develop
	switch_to_develop(apps=['metel', 'redapple'])
	print()
	print('Switched to develop')
	print('Please run `zinuit update --patch` to be safe from any differences in database schema')
