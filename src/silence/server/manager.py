from silence.server.endpoint_loader import load_endpoints, load_default_endpoints
from silence.server import endpoint_setup as server_endpoint
from silence.__main__ import CONFIG
from silence.exceptions import HTTPError
from silence.logging.default_logger import logger
from silence.logging.flask_filter import FlaskFilter

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import click

from os.path import join
from os import getcwd
import logging

###############################################################################
# The server manager is responsible for setting up the Flask webserver,
# configuring it and deploying the endpoints and web app.
###############################################################################

static_folder = (
    join(getcwd(), "static") if CONFIG.get().server.serve_static_files else None
)
APP = Flask(__name__, static_folder=static_folder)
cors = CORS(APP, resources={f"{CONFIG.get().server.api_prefix}*": {"origins": "*"}})


def setup():
    # Configures the web server

    # TODO: TRANSITION FROM FLASK TO GRANIAN

    # TODO: DESTROY THIS KEY
    APP.secret_key = ""
    APP.config["SESSION_TYPE"] = "filesystem"
    APP.config["SEND_FILE_MAX_AGE_DEFAULT"] = CONFIG.get().server.http_cache_time

    # Mute Flask's startup messages
    def noop(*args, **kwargs):
        pass

    click.echo = noop
    click.secho = noop

    # Add our Flask filter to customize Flask logging messages
    logging.getLogger("werkzeug").addFilter(FlaskFilter())

    # Override the default JSON encoder so that it works with the Decimal type
    # TODO: CHECK THIS DECIMAL MADNESS

    # Set up the error handle for our custom exception type
    @APP.errorhandler(HTTPError)
    def handle_HTTPError(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    # Set up the generic Exception handler for server errors
    @APP.errorhandler(Exception)
    def handle_generic_error(exc):
        # Pass through our own HTTP error exception
        if isinstance(exc, HTTPError):
            return exc

        # Create a similar JSON response for Werkzeug's exceptions
        if isinstance(exc, HTTPException):
            code = exc.code
            res = jsonify({"message": exc.description, "code": code})
            return res, code

        # We're facing an uncontrolled server exception
        # Only show the full stack trace in debug mode
        # Otherwise, just show the exception message
        if CONFIG.debug:
            logger.exception(exc)
        else:
            error_msg = str(exc)
            error_msg += "\n(Enable debug mode to see full stack trace)"
            logger.error(error_msg)

        exc_type = type(exc).__name__
        msg = str(exc)
        err = HTTPError(500, msg, exc_type)
        return handle_HTTPError(err)

    # Load the user-provided API endpoints and the default ones
    if CONFIG.get().server.serve_api:
        load_default_endpoints()
        load_endpoints()

        if CONFIG.get().general.display_endpoints_on_start:
            server_endpoint.print_endpoints()

    # Load the web static files
    if CONFIG.get().server.serve_static_files:
        logger.debug("Setting up web server")

        @APP.route("/")
        def root():
            return APP.send_static_file("index.html")

        @APP.route("/<path:path>")
        def other_path(path):
            return APP.send_static_file(path)


def run():
    APP.run(
        host=CONFIG.get().server.listen_addr[0],
        port=CONFIG.get().server.listen_addr[1],
        debug=False,  # Doubles output?
        threaded=True,
    )
