from silence.__main__ import CONFIG
from silence.cli.template_retrieve import download_from_github


def handle(args):
    args = vars(args)  # Convert the Namespace object into a dict

    if all(not args[k] for k in ("blank", "url", "template")):
        # No extra args provided, use the default template
        args["template"] = CONFIG.general.default_template[1]
    elif args["blank"]:
        args["template"] = "blank"

    template = args["template"]
    project_name = args["name"]

    if template:
        repo_url = f"https://github.com/{CONFIG.general.default_template[0]}/silence-template-v2-{CONFIG.general.default_template[1]}"
    else:
        # We have to download a repo from a URL
        repo_url = args["url"]

    download_from_github(project_name, repo_url)
    extra_text = (
        f"using the template '{template}'" if template else "from the provided repo"
    )
    print(f'The Silence project "{project_name}" has been created {extra_text}.')
