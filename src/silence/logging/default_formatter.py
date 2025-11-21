from silence.utils import append_color_log

from colorama import Fore, Style

import logging


class DefaultFormatter(logging.Formatter):
    format_nolvl = "%(message)s"
    format_lvl = "[%(levelname)s] %(message)s"

    FORMATS = {
        logging.DEBUG: append_color_log(Fore.BLACK, format_lvl),
        logging.INFO: format_nolvl,
        logging.WARNING: append_color_log(Fore.YELLOW, format_lvl),
        logging.ERROR: append_color_log(Fore.RED, format_lvl),
        logging.CRITICAL: append_color_log(Fore.RED, format_lvl),
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        res = formatter.format(record)

        # If we're logging an exception, print the stack trace in red
        if record.exc_info:
            res = res.replace(Style.RESET_ALL, "")
            res += Style.RESET_ALL

        return res
