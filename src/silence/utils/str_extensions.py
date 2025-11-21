from silence.__main__ import CONFIG

from colorama import Style


def append_color_log(color, string):
    if CONFIG.get().general.colored_output:
        return Style.BRIGHT + color + string + Style.RESET_ALL
    else:
        return string
