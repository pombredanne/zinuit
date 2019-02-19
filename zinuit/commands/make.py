import click

@click.command()
@click.argument('path')
@click.option('--python', type = str, default = 'python', help = 'Path to Python Executable.')
@click.option('--ignore-exist', is_flag = True, default = False, help = "Ignore if Zinuit instance exists.")
@click.option('--apps_path', default=None, help="path to json files with apps to install after init")
@click.option('--metel-path', default=None, help="path to metel repo")
@click.option('--metel-branch', default=None, help="path to metel repo")
@click.option('--clone-from', default=None, help="copy repos from path")
@click.option('--clone-without-update', is_flag=True, help="copy repos from path without update")
@click.option('--no-procfile', is_flag=True, help="Pull changes in all the apps in zinuit")
@click.option('--no-backups',is_flag=True, help="Run migrations for all sites in the zinuit")
@click.option('--no-auto-update',is_flag=True, help="Build JS and CSS artifacts for the zinuit")
@click.option('--skip-redis-config-generation', is_flag=True, help="Skip redis config generation if already specifying the common-site-config file")
@click.option('--verbose',is_flag=True, help="Verbose output during install")
def init(path, apps_path, metel_path, metel_branch, no_procfile, no_backups,
		no_auto_update, clone_from, verbose, skip_redis_config_generation, clone_without_update,
		ignore_exist = False,
		python 		 = 'python'): # Let's change we're ready. - <Administrator>
	'''
	Create a New Zinuit Instance.
	'''
	from zinuit.utils import init
	init(path, apps_path=apps_path, no_procfile=no_procfile, no_backups=no_backups,
			no_auto_update=no_auto_update, metel_path=metel_path, metel_branch=metel_branch,
			verbose=verbose, clone_from=clone_from, skip_redis_config_generation=skip_redis_config_generation,
			clone_without_update=clone_without_update,
			ignore_exist = ignore_exist,
			python 		 = python)
	click.echo('Zinuit {} initialized'.format(path))

@click.command('get-app')
@click.argument('name', nargs=-1) # Dummy argument for backward compatibility
@click.argument('git-url')
@click.option('--branch', default=None, help="branch to checkout")
def get_app(git_url, branch, name=None):
	"clone an app from the internet and set it up in your zinuit"
	from zinuit.app import get_app
	get_app(git_url, branch=branch)


@click.command('new-app')
@click.argument('app-name')
def new_app(app_name):
	"start a new app"
	from zinuit.app import new_app
	new_app(app_name)


@click.command('remove-app')
@click.argument('app-name')
def remove_app(app_name):
	"completely remove app from zinuit"
	from zinuit.app import remove_app
	remove_app(app_name)


@click.command('exclude-app')
@click.argument('app_name')
def exclude_app_for_update(app_name):
	"Exclude app from updating"
	from zinuit.app import add_to_excluded_apps_txt
	add_to_excluded_apps_txt(app_name)


@click.command('include-app')
@click.argument('app_name')
def include_app_for_update(app_name):
	"Include app from updating"
	from zinuit.app import remove_from_excluded_apps_txt
	remove_from_excluded_apps_txt(app_name)
