import logging
from silence.sql.tables import DATABASE_SCHEMA, TableField
from silence.logging.default_logger import logger
from silence.__main__ import CONFIG
from silence.server.endpoint_setup import ENDPOINTS, Endpoints
from silence.server.endpoint import EndpointDefinition, HttpMethod

from typing import List, Dict

from os import listdir, getcwd, path, mkdir, makedirs
import re

from msgspec import toml


# Entry point for the CLI command
def create_api():
    load_endpoints()
    generate_db_endpoints()


# TODO: GENERATE ENDPOINTS ON RUNTIME WITHOUT READING FROM THE _auto file


# Get the entities from the database and the existing user endpoints and
# create CRUD endpoint files (json) for the remaining o  nes.
def generate_db_endpoints():
    # Load the database's schema
    DATABASE_SCHEMA.load_tables()

    # Remove the folder if it exists and create it again
    auto_dir = getcwd() + "/endpoints/_auto"

    logger.debug("Creating directory %s", auto_dir)
    try:
        makedirs(auto_dir)
    except OSError:
        logger.debug("Directory already exists.")

    # Generate endpoints for each table
    for table in DATABASE_SCHEMA.tables:
        endpoints: Dict[str, EndpointDefinition] = dict()
        logger.info("Generating endpoints for %s", table.name)

        route_one = "/{}/${}".format(table.name.casefold(), table.primary_key_field)
        route_all = "/{}".format(table.name.casefold())

        # endpoints_schema = [
        #     ("GET", "getAll", route_all),
        #     ("GET", "getById", route_one),
        #     ("POST", "create", route_all),
        #     ("PUT", "update", route_one),
        #     ("DELETE", "delete", route_one),
        # ]

        # example:
        # [('GET', 'getAll', '/departments'),
        #  ('GET', 'getById', '/departments/$departmentId'),
        #  ('POST', 'create', '/departments'),
        #  ('PUT', 'update', '/departments/$departmentId'),
        #  ('DELETE', 'delete', '/departments/$departmentId')]

        for method in HttpMethod:
            match method:
                case HttpMethod.GET if table.is_view:
                    ENDPOINTS.put(
                        "_generated_{}_getAll".format(table.name.casefold()),
                        EndpointDefinition(
                            route_all,
                            HttpMethod.GET,
                            "SELECT * FROM {}".format(table.name),
                            "Gets all entries from '{}'.".format(table.name),
                            _generated=True,
                        ),
                    )
                case HttpMethod.GET if not table.is_view:
                    ENDPOINTS.put(
                        "_generated_{}_getAll".format(table.name.casefold()),
                        EndpointDefinition(
                            route_all,
                            HttpMethod.GET,
                            "SELECT * FROM {}".format(table.name),
                            "Gets all entries from '{}'.".format(table.name),
                            _generated=True,
                        ),
                    )
                    ENDPOINTS.put(
                        "_generated_{}_getById".format(table.name.casefold()),
                        EndpointDefinition(
                            route_one,
                            HttpMethod.GET,
                            "SELECT * FROM {} WHERE {} = ${}".format(
                                table.name,
                                table.primary_key_field,
                                table.primary_key_field,
                            ),
                            "Gets an entry from '{}' by its primary key.".format(
                                table.name
                            ),
                            _generated=True,
                        ),
                    )
                case HttpMethod.POST if not table.is_view:
                    ENDPOINTS.put(
                        "_generated_{}_create".format(table.name.casefold()),
                        EndpointDefinition(
                            route_all,
                            HttpMethod.POST,
                            "INSERT INTO {} {} VALUES {}".format(
                                table.name,
                                params_to_string(table.fields),
                                params_to_string(table.fields, "$"),
                            ),
                            "Creates a new entry in '{}'.".format(table.name),
                            [field.name for field in table.fields],
                            # TODO: set this field when auth handling is created
                            # required_auth=CONFIG.get().app.auth.enable,
                            _generated=True,
                        ),
                    )

                case HttpMethod.PUT if not table.is_view:
                    ENDPOINTS.put(
                        "_generated_{}_update".format(table.name.casefold()),
                        EndpointDefinition(
                            route_one,
                            HttpMethod.PUT,
                            "UPDATE {} SET {} WHERE {} = ${}".format(
                                table.name,
                                params_to_string(table.fields, is_update=True),
                                table.primary_key_field,
                                table.primary_key_field,
                            ),
                            "Updates an existing entry in '{}' by its primary key.".format(
                                table.name
                            ),
                            [field.name for field in table.fields],
                            # TODO: set this field when auth handling is created
                            # required_auth=CONFIG.get().app.auth.enable,
                            _generated=True,
                        ),
                    )

                case HttpMethod.DELETE if not table.is_view:
                    ENDPOINTS.put(
                        "_generated_{}_delete".format(table.name.casefold()),
                        EndpointDefinition(
                            route_one,
                            HttpMethod.DELETE,
                            "DELETE FROM {} WHERE {} = ${}".format(
                                table.name,
                                table.primary_key_field,
                                table.primary_key_field,
                            ),
                            "Deletes an existing entry in '{}' by its primary key.".format(
                                table.name
                            ),
                            # TODO: set this field when auth handling is created
                            # required_auth=CONFIG.get().app.auth.enable,
                            _generated=True,
                        ),
                    )

        # Create *all* the .js files for the API.
        # TODO: FIX THIS
        # generate_API_file_for_endpoints(endpoints_to_js, table.name, pk)

        # Dump the auto generated endpoints to a toml file
        if endpoints:
            with open(auto_dir + f"/{table.name}.toml", "wb") as f:
                f.write(toml.encode(endpoints))

    # Finally, generate the .js API module for the allowed auth operations
    auth_endpoints = {}
    if CONFIG.get().app.auth.enable:
        auth_endpoints["login"] = {
            "route": "/login",
            "method": "POST",
            "description": "Logs in using an identifier and password",
        }

    if CONFIG.get().app.auth.allow_signup:
        auth_endpoints["register"] = {
            "route": "/register",
            "method": "POST",
            "description": "Registers a new user and stores the password safely in the database",
        }

    if auth_endpoints:
        generate_API_file_for_endpoints(auth_endpoints, "auth", None)


# Create generic .js files to consume the created endpoints.
def generate_API_file_for_endpoints(endpoints, table_name, pk_name):
    api_path = getcwd() + "/web/js/api"

    if not path.isdir(api_path):
        makedirs(api_path)

    functions = [
        generate_api_text(ep_name, pk_name, ep_data)
        for ep_name, ep_data in endpoints.items()
    ]
    functions_str = "\n\n    ".join(functions)

    file_content = f"""/*
 * DO NOT EDIT THIS FILE, it is auto-generated. It will be updated automatically.
 * All changes done to this file will be lost upon re-running the 'silence createapi' command.
 * If you want to create new API methods, define them in a new file.
 *
 * Silence is built and maintained by the DEAL research group at the University of Seville.
 * You can find us at https://deal.us.es
 */

"use strict";

import {{ BASE_URL, requestOptions }} from './common.js';

const {table_name}API_auto = {{

    {functions_str}
}};

export {{ {table_name}API_auto }};"""

    open(f"{api_path}/_{table_name}.js", "w", encoding="utf8").write(file_content)


def generate_api_text(name, pk_name, endpoint_data):
    method = endpoint_data["method"].lower()
    route = endpoint_data["route"]
    description = endpoint_data["description"]

    # Replace the URL params with JS's string interpolation method
    if "$" in route:
        route = re.sub(r"\$(\w+)", r"${\1}", route)

    is_getById = name == "getById"
    needs_formdata = method in ("post", "put")
    formdata = ", formData" if needs_formdata else ""

    args = []
    if needs_formdata:
        args.append("formData")

    if method in ("put", "delete") or is_getById:
        args.append(pk_name)

    return f"""/** {description} */
    {name}: async function({", ".join(args)}) {{
        let response = await axios.{method}(`${{BASE_URL}}{route}`{formdata}, requestOptions);
        return response.data{"[0]" if is_getById else ""};
    }},"""


def load_endpoints():
    endpoints_dir = getcwd() + "/endpoints"

    logger.debug("Looking for endpoints at {}".format(endpoints_dir))

    # Create the endpoints dir if its not there
    if not path.isdir(endpoints_dir):
        mkdir(endpoints_dir)

    # Get every .toml file in the directory
    endpoint_files = [
        endpoints_dir + f"/{f}" for f in listdir(endpoints_dir) if f.endswith(".toml")
    ]

    for file in endpoint_files:
        with open(file, "r", encoding="utf8") as f:
            try:
                endpoints: Dict[str, EndpointDefinition] = toml.decode(
                    f.read(), type=Endpoints
                )
                # Check whether endpoints names contain '_generated' or are marked as _auto
                if any(
                    name.startswith("_generated") or endpoint_def._generated
                    for name, endpoint_def in endpoints.items()
                ):
                    raise Exception(
                        "Endpoint's name cannot start with '_generated' or "
                        "be marked as _generated."
                    )
                for name, endpoint in endpoints.items():
                    ENDPOINTS.put(name, endpoint, ignore_if_exists=False)
            except Exception as e:
                e.add_note("Cannot deserialize endpoint definition.")
                raise e


def params_to_string(param_list: List[TableField], char_add="", is_update=False):
    def add_pref(x):
        return char_add + x if not is_update else f"{x} = ${x}"

    res = ", ".join(add_pref(x.name) for x in param_list)
    return f"({res})" if not is_update else res
