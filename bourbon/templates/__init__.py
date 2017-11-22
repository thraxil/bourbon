from paste.script import templates
import pkg_resources

class BourbonApp(templates.Template):
    egg_plugins = ["BourbonApp"]
    _template_dir = 'bourbonapp'
    summary = "BourbonApp template"
    required_templates = ["basic_package"]
	  
