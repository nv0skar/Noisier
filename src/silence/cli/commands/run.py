from silence.logging.default_logger import logger
from silence.config import ConfigError
from silence.__main__ import CONFIG
from silence.server import endpoint_parser, manager as server_manager
from silence.server.endpoint_setup import ENDPOINTS
from silence.utils.check_update import check_for_new_version
from silence.__version__ import __version__


def handle(args):
    logger.info("Silence v%s", __version__)
    logger.debug("Current settings:\n%s", CONFIG.get())

    new_ver = check_for_new_version()
    if new_ver:
        logger.warning(
            "A new Silence version (v%s) is available. Run 'pip install --upgrade Silence' to upgrade.",
            new_ver,
        )
        logger.warning(
            "To see what's new, visit: https://github.com/DEAL-US/Silence/blob/master/CHANGELOG.md"
        )

    # Check settings consistency relative to server execution
    if not (CONFIG.get().server.serve_api or CONFIG.get().server.serve_static_files):
        raise ConfigError(
            "Inconsistent settings error: both 'serve_api' and 'serve_static_files' are set to false, "
            "which means neither the api or the static file server will run."
        )

    if not CONFIG.get().app.auth.enable and (
        CONFIG.get().app.admin_panel or CONFIG.get().app.auth.allow_signup
    ):
        raise ConfigError(
            "Inconsistent settings error: cannot enable the admin panel if authentication "
            "is disabled."
        )

    endpoint_parser.create_api()
    server_manager.setup()
    server_manager.run()
