import re

from jinja2 import Environment, FileSystemLoader


def make_replacer(template_kwargs):
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        return str(template_kwargs[key])

    return replacer


def generate_plugin(emoji_dir, emoji_load_limit):
    base_plugin_name = "universal-emoji"
    fname = f"{base_plugin_name}.template.ini"
    out_fname = f"{base_plugin_name}.autogenerated.ini"

    autogenerated_warning = "WARNING: this file is generated automatically. Changes will not persist. Change the template file or generator code itself to persist changes"
    template_kwargs = {
        "emoji_dir": emoji_dir,
        "emoji_load_limit": emoji_load_limit,
        "autogenerated_warning": autogenerated_warning,
    }
    with open(fname, "r") as template:
        template_str = template.read()
        rendered = re.sub(
            r"{{\s*([\w_]+)\s*}}", make_replacer(template_kwargs), template_str
        )
    with open(out_fname, "w") as render_file:
        render_file.write(rendered)
