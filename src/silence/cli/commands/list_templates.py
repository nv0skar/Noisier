from silence.__main__ import CONFIG
from silence.logging.default_logger import logger

import traceback
import requests


def handle(args):
    query_url = (
        f"https://api.github.com/orgs/{CONFIG.get().general.default_template[0]}/repos"
    )

    try:
        repo_data = requests.get(query_url, timeout=10).json()
    except Exception as e:
        e.add_note(
            "An error has occurred when querying GitHub's API to obtain the list of templates."
        )
        logger.debug(traceback.format_exc())
        raise e

    templates = []
    for repo in repo_data:
        name = repo["name"].lower()
        if name.startswith("silence-template-v2-"):
            template_name = name.replace("silence-template-v2-", "")
            desc = repo["description"]
            templates.append({"name": template_name, "desc": desc})

    templates.sort(key=lambda x: x["name"])

    print("Available templates:")
    for tmpl in templates:
        name = tmpl["name"]
        default = (
            " (default)"
            if name == CONFIG.get().general.default_template[1].lower()
            else ""
        )
        desc = f": {tmpl['desc']}" if tmpl["desc"] else ""

        print(f"    · {name}{default}{desc}")
