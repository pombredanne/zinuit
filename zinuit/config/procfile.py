import zinuit, os, click
from zinuit.utils import find_executable
from zinuit.app import use_rq
from zinuit.config.common_site_config import get_config

def setup_procfile(zinuit_path, yes=False):
	config = get_config(zinuit_path=zinuit_path)
	procfile_path = os.path.join(zinuit_path, 'Procfile')
	if not yes and os.path.exists(procfile_path):
		click.confirm('A Procfile already exists and this will overwrite it. Do you want to continue?',
			abort=True)

	procfile = zinuit.env.get_template('Procfile').render(
		node=find_executable("node") or find_executable("nodejs"),
		use_rq=use_rq(zinuit_path),
		webserver_port=config.get('webserver_port'),
		CI=os.environ.get('CI'))

	with open(procfile_path, 'w') as f:
		f.write(procfile)
