import os, sys, shutil, subprocess, logging, itertools, requests, json, platform, select, pwd, grp, multiprocessing, hashlib
from distutils.spawn import find_executable
import zinuit
import semantic_version
from zinuit import env
from six import iteritems


class PatchError(Exception):
	pass

class CommandFailedError(Exception):
	pass

logger = logging.getLogger(__name__)

folders_in_zinuit = ('apps', 'sites', 'config', 'logs', 'config/pids')

def safe_decode(string, encoding = 'utf-8'):
	try:
		string = string.decode(encoding)
	except Exception:
		pass
	return string

def get_metel(zinuit_path='.'):
	metel = get_env_cmd('metel', zinuit_path=zinuit_path)
	if not os.path.exists(metel):
		print('metel app is not installed. Run the following command to install metel')
		print('zinuit get-app https://github.com/amonak/metel.git')
	return metel

def get_env_cmd(cmd, zinuit_path='.'):
	return os.path.abspath(os.path.join(zinuit_path, 'env', 'bin', cmd))

def init(path, apps_path=None, no_procfile=False, no_backups=False,
		no_auto_update=False, metel_path=None, metel_branch=None, wheel_cache_dir=None,
		verbose=False, clone_from=None, skip_redis_config_generation=False,
		clone_without_update=False,
		ignore_exist = False,
		python		 = 'python'): # Let's change when we're ready. - <Administrator>
	from .app import get_app, install_apps_from_path
	from .config.common_site_config import make_config
	from .config import redis
	from .config.procfile import setup_procfile
	from zinuit.patches import set_all_patches_executed

	import os.path as osp

	if osp.exists(path):
		if not ignore_exist:
			raise ValueError('Zinuit Instance {path} already exists.'.format(path = path))
	else:
		os.makedirs(path)

	for dirname in folders_in_zinuit:
		try:
			os.makedirs(os.path.join(path, dirname))
		except OSError as e:
			if e.errno == os.errno.EEXIST:
				pass

	setup_logging()

	setup_env(zinuit_path=path, python = python)

	make_config(path)

	if clone_from:
		clone_apps_from(zinuit_path=path, clone_from=clone_from, update_app=not clone_without_update)
	else:
		if not metel_path:
			metel_path = 'https://github.com/amonak/metel.git'

		get_app(metel_path, branch=metel_branch, zinuit_path=path, build_asset_files=False, verbose=verbose)

		if apps_path:
			install_apps_from_path(apps_path, zinuit_path=path)


	zinuit.set_metel_version(zinuit_path=path)
	if zinuit.METEL_VERSION > 1:
		update_node_packages(zinuit_path=path)

	set_all_patches_executed(zinuit_path=path)
	build_assets(zinuit_path=path)

	if not skip_redis_config_generation:
		redis.generate_config(path)

	if not no_procfile:
		setup_procfile(path)
	if not no_backups:
		setup_backups(zinuit_path=path)
	if not no_auto_update:
		setup_auto_update(zinuit_path=path)
	copy_patches_txt(path)

def copy_patches_txt(zinuit_path):
	shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'patches', 'patches.txt'),
		os.path.join(zinuit_path, 'patches.txt'))

def clone_apps_from(zinuit_path, clone_from, update_app=True):
	from .app import install_app
	print('Copying apps from {0}...'.format(clone_from))
	subprocess.check_output(['cp', '-R', os.path.join(clone_from, 'apps'), zinuit_path])

	node_modules_path = os.path.join(clone_from, 'node_modules')
	if os.path.exists(node_modules_path):
		print('Copying node_modules from {0}...'.format(clone_from))
		subprocess.check_output(['cp', '-R', node_modules_path, zinuit_path])

	def setup_app(app):
		# run git reset --hard in each branch, pull latest updates and install_app
		app_path = os.path.join(zinuit_path, 'apps', app)

		# remove .egg-ino
		subprocess.check_output(['rm', '-rf', app + '.egg-info'], cwd=app_path)

		if update_app and os.path.exists(os.path.join(app_path, '.git')):
			remotes = subprocess.check_output(['git', 'remote'], cwd=app_path).strip().split()
			if 'upstream' in remotes:
				remote = 'upstream'
			else:
				remote = remotes[0]
			print('Cleaning up {0}'.format(app))
			branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=app_path).strip()
			subprocess.check_output(['git', 'reset', '--hard'], cwd=app_path)
			subprocess.check_output(['git', 'pull', '--rebase', remote, branch], cwd=app_path)

		install_app(app, zinuit_path)

	with open(os.path.join(clone_from, 'sites', 'apps.txt'), 'r') as f:
		apps = f.read().splitlines()

	for app in apps:
		setup_app(app)

def exec_cmd(cmd, cwd='.'):
	from .cli import from_command_line

	is_async = False if from_command_line else True
	if is_async:
		stderr = stdout = subprocess.PIPE
	else:
		stderr = stdout = None

	logger.info(cmd)

	p = subprocess.Popen(cmd, cwd=cwd, shell=True, stdout=stdout, stderr=stderr,
		universal_newlines=True)

	if is_async:
		return_code = print_output(p)
	else:
		return_code = p.wait()

	if return_code > 0:
		raise CommandFailedError(cmd)

def which(executable, raise_err = False):
	from distutils.spawn import find_executable
	exec_ = find_executable(executable)

	if not exec_ and raise_err:
		raise ValueError('{executable} not found.'.format(
			executable = executable
		))

	return exec_

def setup_env(zinuit_path='.', python = 'python'):
	python = which(python, raise_err = True)
	pip    = os.path.join('env', 'bin', 'pip')

	exec_cmd('virtualenv -q {} -p {}'.format('env', python), cwd=zinuit_path)
	exec_cmd('{} -q install --upgrade pip'.format(pip), cwd=zinuit_path)
	exec_cmd('{} -q install wheel'.format(pip), cwd=zinuit_path)
	exec_cmd('{} -q install six'.format(pip), cwd=zinuit_path)
	exec_cmd('{} -q install pdfkit'.format(pip), cwd=zinuit_path)

def setup_socketio(zinuit_path='.'):
	exec_cmd("npm install socket.io redis express superagent cookie babel-core less chokidar \
		babel-cli babel-preset-es2015 babel-preset-es2016 babel-preset-es2017 babel-preset-babili", cwd=zinuit_path)

def patch_sites(zinuit_path='.'):
	zinuit.set_metel_version(zinuit_path=zinuit_path)

	try:
		if zinuit.METEL_VERSION == 0:
			exec_cmd("{metel} --latest all".format(metel=get_metel(zinuit_path=zinuit_path)), cwd=os.path.join(zinuit_path, 'sites'))
		else:
			run_metel_cmd('--site', 'all', 'migrate', zinuit_path=zinuit_path)
	except subprocess.CalledProcessError:
		raise PatchError

def build_assets(zinuit_path='.'):
	zinuit.set_metel_version(zinuit_path=zinuit_path)

	if zinuit.METEL_VERSION == 0:
		exec_cmd("{metel} --build".format(metel=get_metel(zinuit_path=zinuit_path)), cwd=os.path.join(zinuit_path, 'sites'))
	else:
		run_metel_cmd('build', zinuit_path=zinuit_path)

def get_sites(zinuit_path='.'):
	sites_dir = os.path.join(zinuit_path, "sites")
	sites = [site for site in os.listdir(sites_dir)
		if os.path.isdir(os.path.join(sites_dir, site)) and site not in ('assets',)]
	return sites

def get_sites_dir(zinuit_path='.'):
	return os.path.abspath(os.path.join(zinuit_path, 'sites'))

def get_zinuit_dir(zinuit_path='.'):
	return os.path.abspath(zinuit_path)

def setup_auto_update(zinuit_path='.'):
	logger.info('setting up auto update')
	add_to_crontab('0 10 * * * cd {zinuit_dir} &&  {zinuit} update --auto >> {logfile} 2>&1'.format(zinuit_dir=get_zinuit_dir(zinuit_path=zinuit_path),
		zinuit=os.path.join(get_zinuit_dir(zinuit_path=zinuit_path), 'env', 'bin', 'zinuit'),
		logfile=os.path.join(get_zinuit_dir(zinuit_path=zinuit_path), 'logs', 'auto_update_log.log')))

def setup_backups(zinuit_path='.'):
	logger.info('setting up backups')
	zinuit_dir = get_zinuit_dir(zinuit_path=zinuit_path)
	zinuit.set_metel_version(zinuit_path=zinuit_path)

	if zinuit.METEL_VERSION == 0:
		backup_command = "cd {sites_dir} && {metel} --backup all".format(metel=get_metel(zinuit_path=zinuit_path),)
	else:
		backup_command = "cd {zinuit_dir} && {zinuit} --site all backup".format(zinuit_dir=zinuit_dir, zinuit=sys.argv[0])

	add_to_crontab('0 */6 * * *  {backup_command} >> {logfile} 2>&1'.format(backup_command=backup_command,
		logfile=os.path.join(get_zinuit_dir(zinuit_path=zinuit_path), 'logs', 'backup.log')))

def add_to_crontab(line):
	current_crontab = read_crontab()
	line = str.encode(line)
	if not line in current_crontab:
		cmd = ["crontab"]
		if platform.system() == 'FreeBSD':
			cmd = ["crontab", "-"]
		s = subprocess.Popen(cmd, stdin=subprocess.PIPE)
		s.stdin.write(current_crontab)
		s.stdin.write(line + b'\n')
		s.stdin.close()

def read_crontab():
	s = subprocess.Popen(["crontab", "-l"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
	out = s.stdout.read()
	s.stdout.close()
	return out

def update_zinuit():
	logger.info('updating zinuit')

	# zenmetweb folder
	cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

	exec_cmd("git pull", cwd=cwd)

def setup_sudoers(user):
	if not os.path.exists('/etc/sudoers.d'):
		os.makedirs('/etc/sudoers.d')

		set_permissions = False
		if not os.path.exists('/etc/sudoers'):
			set_permissions = True

		with open('/etc/sudoers', 'a') as f:
			f.write('\n#includedir /etc/sudoers.d\n')

		if set_permissions:
			os.chmod('/etc/sudoers', 0o440)

	sudoers_file = '/etc/sudoers.d/metel'

	template = env.get_template('metel_sudoers')
	metel_sudoers = template.render(**{
		'user': user,
		'service': find_executable('service'),
		'systemctl': find_executable('systemctl'),
		'supervisorctl': find_executable('supervisorctl'),
		'nginx': find_executable('nginx'),
		'zinuit': find_executable('zinuit')
	})
	metel_sudoers = safe_decode(metel_sudoers)

	with open(sudoers_file, 'w') as f:
		f.write(metel_sudoers)

	os.chmod(sudoers_file, 0o440)

def setup_logging(zinuit_path='.'):
	if os.path.exists(os.path.join(zinuit_path, 'logs')):
		logger = logging.getLogger('zinuit')
		log_file = os.path.join(zinuit_path, 'logs', 'zinuit.log')
		formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
		hdlr = logging.FileHandler(log_file)
		hdlr.setFormatter(formatter)
		logger.addHandler(hdlr)
		logger.setLevel(logging.DEBUG)

def get_program(programs):
	program = None
	for p in programs:
		program = find_executable(p)
		if program:
			break
	return program

def get_process_manager():
	return get_program(['foreman', 'forego', 'honcho'])

def start(no_dev=False, concurrency=None):
	program = get_process_manager()
	if not program:
		raise Exception("No process manager found")
	os.environ['PYTHONUNBUFFERED'] = "true"
	if not no_dev:
		os.environ['DEV_SERVER'] = "true"

	command = [program, 'start']
	if concurrency:
		command.extend(['-c', concurrency])

	os.execv(program, command)

def check_cmd(cmd, cwd='.'):
	try:
		subprocess.check_call(cmd, cwd=cwd, shell=True)
		return True
	except subprocess.CalledProcessError:
		return False

def get_git_version():
	'''returns git version from `git --version`
	extracts version number from string `get version 1.9.1` etc'''
	version = get_cmd_output("git --version")
	version = safe_decode(version)
	version = version.strip().split()[2]
	version = '.'.join(version.split('.')[0:2])
	return float(version)

def check_git_for_shallow_clone():
	from .config.common_site_config import get_config
	config = get_config('.')

	if config.get('release_zinuit'):
		return False

	if not config.get('shallow_clone'):
		return False

	git_version = get_git_version()
	if git_version > 1.9:
		return True
	return False

def get_cmd_output(cmd, cwd='.'):
	try:
		output = subprocess.check_output(cmd, cwd=cwd, shell=True, stderr=subprocess.PIPE).strip()
		output = output.decode('utf-8')
		return output
	except subprocess.CalledProcessError as e:
		if e.output:
			print(e.output)
		raise

def safe_encode(what, encoding = 'utf-8'):
	try:
		what = what.encode(encoding)
	except Exception:
		pass

	return what

def restart_supervisor_processes(zinuit_path='.', web_workers=False):
	from .config.common_site_config import get_config
	conf = get_config(zinuit_path=zinuit_path)
	zinuit_name = get_zinuit_name(zinuit_path)

	cmd = conf.get('supervisor_restart_cmd')
	if cmd:
		exec_cmd(cmd, cwd=zinuit_path)

	else:
		supervisor_status = subprocess.check_output(['sudo', 'supervisorctl', 'status'], cwd=zinuit_path)
		supervisor_status = safe_decode(supervisor_status)

		if web_workers and '{zinuit_name}-web:'.format(zinuit_name=zinuit_name) in supervisor_status:
			group = '{zinuit_name}-web:	'.format(zinuit_name=zinuit_name)

		elif '{zinuit_name}-workers:'.format(zinuit_name=zinuit_name) in supervisor_status:
			group = '{zinuit_name}-workers: {zinuit_name}-web:'.format(zinuit_name=zinuit_name)

		# backward compatibility
		elif '{zinuit_name}-processes:'.format(zinuit_name=zinuit_name) in supervisor_status:
			group = '{zinuit_name}-processes:'.format(zinuit_name=zinuit_name)

		# backward compatibility
		else:
			group = 'metel:'

		exec_cmd('sudo supervisorctl restart {group}'.format(group=group), cwd=zinuit_path)

def restart_systemd_processes(zinuit_path='.', web_workers=False):
	from .config.common_site_config import get_config
	conf = get_config(zinuit_path=zinuit_path)
	zinuit_name = get_zinuit_name(zinuit_path)
	exec_cmd('sudo systemctl stop -- $(systemctl show -p Requires {zinuit_name}.target | cut -d= -f2)'.format(zinuit_name=zinuit_name))
	exec_cmd('sudo systemctl start -- $(systemctl show -p Requires {zinuit_name}.target | cut -d= -f2)'.format(zinuit_name=zinuit_name))

def set_default_site(site, zinuit_path='.'):
	if not site in get_sites(zinuit_path=zinuit_path):
		raise Exception("Site not in zinuit")
	exec_cmd("{metel} --use {site}".format(metel=get_metel(zinuit_path=zinuit_path), site=site),
			cwd=os.path.join(zinuit_path, 'sites'))

def update_requirements(zinuit_path='.'):
	print('Updating Python libraries...')
	pip = os.path.join(zinuit_path, 'env', 'bin', 'pip')

	exec_cmd("{pip} install --upgrade pip".format(pip=pip))

	apps_dir = os.path.join(zinuit_path, 'apps')

	# Update zinuit requirements
	zinuit_req_file = os.path.join(os.path.dirname(zinuit.__path__[0]), 'requirements.txt')
	install_requirements(pip, zinuit_req_file)

	from zinuit.app import get_apps, install_app

	for app in get_apps():
		install_app(app, zinuit_path=zinuit_path)

def update_node_packages(zinuit_path='.'):
	print('Updating node packages...')
	from zinuit.app import get_develop_version
	from distutils.version import LooseVersion
	v = LooseVersion(get_develop_version('metel', zinuit_path = zinuit_path))


	# After rollup was merged, metel_version = 3.1
	# if develop_verion is 4 and up, only then install yarn
	if v < LooseVersion('4.x.x-develop'):
		update_npm_packages(zinuit_path)
	else:
		update_yarn_packages(zinuit_path)

def update_yarn_packages(zinuit_path='.'):
	apps_dir = os.path.join(zinuit_path, 'apps')

	if not find_executable('yarn'):
		print("Please install yarn using below command and try again.")
		print("`npm install -g yarn`")
		return

	for app in os.listdir(apps_dir):
		app_path = os.path.join(apps_dir, app)
		if os.path.exists(os.path.join(app_path, 'package.json')):
			exec_cmd('yarn install', cwd=app_path)


def update_npm_packages(zinuit_path='.'):
	apps_dir = os.path.join(zinuit_path, 'apps')
	package_json = {}

	for app in os.listdir(apps_dir):
		package_json_path = os.path.join(apps_dir, app, 'package.json')

		if os.path.exists(package_json_path):
			with open(package_json_path, "r") as f:
				app_package_json = json.loads(f.read())
				# package.json is usually a dict in a dict
				for key, value in iteritems(app_package_json):
					if not key in package_json:
						package_json[key] = value
					else:
						if isinstance(value, dict):
							package_json[key].update(value)
						elif isinstance(value, list):
							package_json[key].extend(value)
						else:
							package_json[key] = value

	if package_json is {}:
		with open(os.path.join(os.path.dirname(__file__), 'package.json'), 'r') as f:
			package_json = json.loads(f.read())

	with open(os.path.join(zinuit_path, 'package.json'), 'w') as f:
		f.write(json.dumps(package_json, indent=1, sort_keys=True))

	exec_cmd('npm install', cwd=zinuit_path)


def install_requirements(pip, req_file):
	if os.path.exists(req_file):
		exec_cmd("{pip} install -q -r {req_file}".format(pip=pip, req_file=req_file))

def backup_site(site, zinuit_path='.'):
	zinuit.set_metel_version(zinuit_path=zinuit_path)

	if zinuit.METEL_VERSION == 0:
		exec_cmd("{metel} --backup {site}".format(metel=get_metel(zinuit_path=zinuit_path), site=site),
				cwd=os.path.join(zinuit_path, 'sites'))
	else:
		run_metel_cmd('--site', site, 'backup', zinuit_path=zinuit_path)

def backup_all_sites(zinuit_path='.'):
	for site in get_sites(zinuit_path=zinuit_path):
		backup_site(site, zinuit_path=zinuit_path)

def is_root():
	if os.getuid() == 0:
		return True
	return False

def set_mariadb_host(host, zinuit_path='.'):
	update_common_site_config({'db_host': host}, zinuit_path=zinuit_path)

def update_common_site_config(ddict, zinuit_path='.'):
	update_json_file(os.path.join(zinuit_path, 'sites', 'common_site_config.json'), ddict)

def update_json_file(filename, ddict):
	if os.path.exists(filename):
		with open(filename, 'r') as f:
			content = json.load(f)

	else:
		content = {}

	content.update(ddict)
	with open(filename, 'w') as f:
		content = json.dump(content, f, indent=1, sort_keys=True)

def drop_privileges(uid_name='nobody', gid_name='nogroup'):
	# from http://stackoverflow.com/a/2699996
	if os.getuid() != 0:
		# We're not root so, like, whatever dude
		return

	# Get the uid/gid from the name
	running_uid = pwd.getpwnam(uid_name).pw_uid
	running_gid = grp.getgrnam(gid_name).gr_gid

	# Remove group privileges
	os.setgroups([])

	# Try setting the new uid/gid
	os.setgid(running_gid)
	os.setuid(running_uid)

	# Ensure a very conservative umask
	os.umask(0o22)

def fix_prod_setup_perms(zinuit_path='.', metel_user=None):
	from .config.common_site_config import get_config
	files = [
		"logs/web.error.log",
		"logs/web.log",
		"logs/workerbeat.error.log",
		"logs/workerbeat.log",
		"logs/worker.error.log",
		"logs/worker.log",
		"config/nginx.conf",
		"config/supervisor.conf",
	]

	if not metel_user:
		metel_user = get_config(zinuit_path).get('metel_user')

	if not metel_user:
		print("metel user not set")
		sys.exit(1)

	for path in files:
		if os.path.exists(path):
			uid = pwd.getpwnam(metel_user).pw_uid
			gid = grp.getgrnam(metel_user).gr_gid
			os.chown(path, uid, gid)

def fix_file_perms():
	for dir_path, dirs, files in os.walk('.'):
		for _dir in dirs:
			os.chmod(os.path.join(dir_path, _dir), 0o755)
		for _file in files:
			os.chmod(os.path.join(dir_path, _file), 0o644)
	bin_dir = './env/bin'
	if os.path.exists(bin_dir):
		for _file in os.listdir(bin_dir):
			if not _file.startswith('activate'):
				os.chmod(os.path.join(bin_dir, _file), 0o755)

def get_current_metel_version(zinuit_path='.'):
	from .app import get_current_metel_version as fv
	return fv(zinuit_path=zinuit_path)

def run_metel_cmd(*args, **kwargs):
	from .cli import from_command_line

	zinuit_path = kwargs.get('zinuit_path', '.')
	f = get_env_cmd('python', zinuit_path=zinuit_path)
	sites_dir = os.path.join(zinuit_path, 'sites')

	is_async = False if from_command_line else True
	if is_async:
		stderr = stdout = subprocess.PIPE
	else:
		stderr = stdout = None

	p = subprocess.Popen((f, '-m', 'metel.utils.zinuit_helper', 'metel') + args,
		cwd=sites_dir, stdout=stdout, stderr=stderr)

	if is_async:
		return_code = print_output(p)
	else:
		return_code = p.wait()

	if return_code > 0:
		sys.exit(return_code)
		#raise CommandFailedError(args)

def get_metel_cmd_output(*args, **kwargs):
	zinuit_path = kwargs.get('zinuit_path', '.')
	f = get_env_cmd('python', zinuit_path=zinuit_path)
	sites_dir = os.path.join(zinuit_path, 'sites')
	return subprocess.check_output((f, '-m', 'metel.utils.zinuit_helper', 'metel') + args, cwd=sites_dir)

def validate_upgrade(from_ver, to_ver, zinuit_path='.'):
	if to_ver >= 2:
		if not find_executable('npm') and not (find_executable('node') or find_executable('nodejs')):
			raise Exception("Please install nodejs and npm")

def pre_upgrade(from_ver, to_ver, zinuit_path='.'):
	pip = os.path.join(zinuit_path, 'env', 'bin', 'pip')

	if from_ver == 0 and to_ver >= 1:
		from .migrate_to_v1 import remove_shopping_cart
		apps = ('metel', 'redapple')
		remove_shopping_cart(zinuit_path=zinuit_path)

		for app in apps:
			cwd = os.path.abspath(os.path.join(zinuit_path, 'apps', app))
			if os.path.exists(cwd):
				exec_cmd("git clean -dxf", cwd=cwd)
				exec_cmd("{pip} install --upgrade -e {app}".format(pip=pip, app=cwd))

def post_upgrade(from_ver, to_ver, zinuit_path='.'):
	from .config.common_site_config import get_config
	from .config import redis
	from .config.supervisor import generate_supervisor_config
	from .config.nginx import make_nginx_conf
	conf = get_config(zinuit_path=zinuit_path)
	print("-"*80)
	print("Your zinuit was upgraded to version {0}".format(to_ver))

	if conf.get('restart_supervisor_on_update'):
		redis.generate_config(zinuit_path=zinuit_path)
		generate_supervisor_config(zinuit_path=zinuit_path)
		make_nginx_conf(zinuit_path=zinuit_path)

		if from_ver == 0 and to_ver == 1:
			setup_backups(zinuit_path=zinuit_path)

		if from_ver <= 1 and to_ver == 2:
			setup_socketio(zinuit_path=zinuit_path)

		print("As you have setup your zinuit for production, you will have to reload configuration for nginx and supervisor")
		print("To complete the migration, please run the following commands")
		print()
		print("sudo service nginx restart")
		print("sudo supervisorctl reload")

def update_translations_p(args):
	try:
		update_translations(*args)
	except requests.exceptions.HTTPError:
		print('Download failed for', args[0], args[1])

def download_translations_p():
	pool = multiprocessing.Pool(4)

	langs = get_langs()
	apps = ('metel', 'redapple')
	args = list(itertools.product(apps, langs))

	pool.map(update_translations_p, args)

def download_translations():
	langs = get_langs()
	apps = ('metel', 'redapple')
	for app, lang in itertools.product(apps, langs):
		update_translations(app, lang)

def get_langs():
	lang_file = 'apps/metel/metel/geo/languages.json'
	with open(lang_file) as f:
		langs = json.loads(f.read())
	return [d['code'] for d in langs]

def update_translations(app, lang):
	translations_dir = os.path.join('apps', app, app, 'translations')
	csv_file = os.path.join(translations_dir, lang + '.csv')
	url = "https://translate.alphamonak.com/files/{}-{}.csv".format(app, lang)
	r = requests.get(url, stream=True)
	r.raise_for_status()

	with open(csv_file, 'wb') as f:
		for chunk in r.iter_content(chunk_size=1024):
			# filter out keep-alive new chunks
			if chunk:
				f.write(chunk)
				f.flush()

	print('downloaded for', app, lang)

def download_chart_of_accounts():
	charts_dir = os.path.join('apps', "redapple", "redapple", 'accounts', 'chart_of_accounts', "submitted")
	csv_file = os.path.join(translations_dir, lang + '.csv')
	url = "https://translate.alphamonak.com/files/{}-{}.csv".format(app, lang)
	r = requests.get(url, stream=True)
	r.raise_for_status()

def print_output(p):
	while p.poll() is None:
		readx = select.select([p.stdout.fileno(), p.stderr.fileno()], [], [])[0]
		send_buffer = []
		for fd in readx:
			if fd == p.stdout.fileno():
				while 1:
					buf = p.stdout.read(1)
					if not len(buf):
						break
					if buf == '\r' or buf == '\n':
						send_buffer.append(buf)
						log_line(''.join(send_buffer), 'stdout')
						send_buffer = []
					else:
						send_buffer.append(buf)

			if fd == p.stderr.fileno():
				log_line(p.stderr.readline(), 'stderr')
	return p.poll()


def log_line(data, stream):
	if stream == 'stderr':
		return sys.stderr.write(data)
	return sys.stdout.write(data)

def get_output(*cmd):
	s = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
	out = s.stdout.read()
	s.stdout.close()
	return out

def before_update(zinuit_path, requirements):
	validate_pillow_dependencies(zinuit_path, requirements)

def validate_pillow_dependencies(zinuit_path, requirements):
	if not requirements:
		return

	try:
		pip = os.path.join(zinuit_path, 'env', 'bin', 'pip')
		exec_cmd("{pip} install Pillow".format(pip=pip))

	except CommandFailedError:
		distro = platform.linux_distribution()
		distro_name = distro[0].lower()
		if "centos" in distro_name or "fedora" in distro_name:
			print("Please install these dependencies using the command:")
			print("sudo yum install libtiff-devel libjpeg-devel libzip-devel freetype-devel lcms2-devel libwebp-devel tcl-devel tk-devel")

			raise

		elif "ubuntu" in distro_name or "elementary os" in distro_name or "debian" in distro_name:
			print("Please install these dependencies using the command:")

			if "ubuntu" in distro_name and distro[1]=="12.04":
				print("sudo apt-get install -y libtiff4-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.5-dev tk8.5-dev python-tk")
			else:
				print("sudo apt-get install -y libtiff5-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python-tk")

			raise

def get_zinuit_name(zinuit_path):
	return os.path.basename(os.path.abspath(zinuit_path))

def setup_fonts():
	fonts_path = os.path.join('/tmp', 'fonts')

	if os.path.exists('/etc/fonts_backup'):
		return

	exec_cmd("git clone https://github.com/amonak/fonts.git", cwd='/tmp')
	os.rename('/etc/fonts', '/etc/fonts_backup')
	os.rename('/usr/share/fonts', '/usr/share/fonts_backup')
	os.rename(os.path.join(fonts_path, 'etc_fonts'), '/etc/fonts')
	os.rename(os.path.join(fonts_path, 'usr_share_fonts'), '/usr/share/fonts')
	shutil.rmtree(fonts_path)
	exec_cmd("fc-cache -fv")

def set_git_remote_url(git_url, zinuit_path='.'):
	"Set app remote git url"
	app = git_url.rsplit('/', 1)[1].rsplit('.', 1)[0]

	if app not in zinuit.app.get_apps(zinuit_path):
		print("No app named {0}".format(app))
		sys.exit(1)

	app_dir = zinuit.app.get_repo_dir(app, zinuit_path=zinuit_path)
	if os.path.exists(os.path.join(app_dir, '.git')):
		exec_cmd("git remote set-url upstream {}".format(git_url), cwd=app_dir)

def run_playbook(playbook_name, extra_vars=None, tag=None):
	if not find_executable('ansible'):
		print("Ansible is needed to run this command, please install it using 'pip install ansible'")
		sys.exit(1)
	args = ['ansible-playbook', '-c', 'local', playbook_name]

	if extra_vars:
		args.extend(['-e', json.dumps(extra_vars)])

	if tag:
		args.extend(['-t', tag])

	subprocess.check_call(args, cwd=os.path.join(os.path.dirname(zinuit.__path__[0]), 'playbooks'))
