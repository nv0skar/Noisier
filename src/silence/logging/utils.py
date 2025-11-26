from silence.__main__ import CONFIG
from silence.logging.default_logger import logger

import colorama
from colorama import Fore, Style

from datetime import datetime
import re

colorama.init()

# Regex to remove ANSI color codes from log lines
RE_ANSI = re.compile(r"(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]")

# Regex to detect server log lines from Flask (werkzeug)
RE_LOG = re.compile(r'(.*) - - \[.*\] "%s" %s %s')
RE_REQ_DATA = re.compile(r"(\w+) (/.*) HTTP.*")

COLORS = {
    "GREEN": Style.BRIGHT + Fore.GREEN if CONFIG.get().general.colored_output else "",
    "MAGENTA": Style.BRIGHT + Fore.MAGENTA
    if CONFIG.get().general.colored_output
    else "",
    "CYAN": Style.BRIGHT + Fore.CYAN if CONFIG.get().general.colored_output else "",
    "YELLOW": Style.BRIGHT + Fore.YELLOW if CONFIG.get().general.colored_output else "",
    "RED": Style.BRIGHT + Fore.RED if CONFIG.get().general.colored_output else "",
    "WHITE": Style.BRIGHT + Fore.WHITE if CONFIG.get().general.colored_output else "",
}
RESET = Style.RESET_ALL if CONFIG.get().general.colored_output else ""


def format_flask_record(record):
    msg = record.msg

    if msg.startswith(" * Running on"):
        record.msg = msg[3:]
        return "running_msg"

    # If the log line is a Flask log line, parse it and
    # style it appropriately
    m = RE_LOG.match(msg)
    if m:
        # The address is parsed from the message
        addr = m.group(1)

        # The rest of the data comes from the args tuple in the log record
        args = record.args
        code = args[1]

        # The address and the route are present in the first arg,
        # but we must remove color codes first before parsing
        addr_and_route = RE_ANSI.sub("", args[0])
        m_addr = RE_REQ_DATA.match(addr_and_route)
        verb = m_addr.group(1)  # type: ignore
        route = m_addr.group(2)  # type: ignore

        if route.startswith(CONFIG.get().server.api_prefix):
            api_web = "[API]"
            api_color = COLORS["MAGENTA"]
        else:
            api_web = "[WEB]"
            api_color = COLORS["CYAN"]

        if code[0] in ("2", "3"):
            code_color = COLORS["GREEN"]
        elif code[0] == "4":
            code_color = COLORS["YELLOW"]
        elif code[0] == "5":
            code_color = COLORS["RED"]
        else:
            code_color = COLORS["WHITE"]

        # Finally, the date is created from scratch here
        date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        record.msg = (
            f"{date} | {api_color}{api_web}{RESET} "
            + f"{verb} {route} from {addr} - {code_color}{code}{RESET}"
        )
        record.args = ()

        return record


def format_custom_record(kind: str, color: str, msg: str):
    if kind.lower() == "api":
        api_web = "[API]"
        api_color = COLORS["MAGENTA"]

    elif kind.lower() == "web":
        api_web = "[WEB]"
        api_color = COLORS["CYAN"]

    try:
        code_color = COLORS[color.upper()]
    except Exception:
        logger.warn(
            "Silence chose a non-existing color for cli message, defaulted to white."
        )
        code_color = COLORS["WHITE"]

    date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    formatted_msg = f"{date} | {api_color}{api_web}{RESET} {code_color}{msg}{RESET}"  # type: ignore

    return formatted_msg
