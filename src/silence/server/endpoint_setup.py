from silence.db import dal
from silence import sql as SQL
from silence.sql import get_sql_op
from silence.__main__ import CONFIG
from silence.server.endpoint import EndpointDefinition
from silence.sql.tables import DATABASE_SCHEMA
from silence.utils.min_type import Min
from silence.auth.tokens import check_token
from silence.logging.default_logger import logger
from silence.logging import utils as log_utils
from silence.sql.converter import silence_to_mysql
from silence.server import manager as server_manager
from silence.exceptions import HTTPError, TokenError

from typing import Optional, Dict, TypeAlias

import re

from flask import jsonify, request


OP_VERBS = {
    SQL.SELECT: "get",
    SQL.INSERT: "post",
    SQL.UPDATE: "put",
    SQL.DELETE: "delete",
}

Endpoints: TypeAlias = Dict[str, EndpointDefinition]


class EndpointsGlobal:
    __slots__ = "_endpoints"

    _endpoints: Dict[str, EndpointDefinition]

    def __init__(self):
        self._endpoints = dict()

    def get_by_route(self, route: str) -> Optional[EndpointDefinition]:
        return next(
            endpoint
            for _, endpoint in self._endpoints.items()
            if endpoint.route == route
        )

    """
    An endpoint will already exist if there is another one that has the same identifier or
    the same route and method.
    """

    def put(
        self,
        name: str,
        endpoint: EndpointDefinition,
        ignore_if_exists: bool = True,
    ):
        for _name, _endpoint in self._endpoints.items():
            if name.casefold() == _name.casefold():
                if not ignore_if_exists and not _endpoint._generated:
                    raise Exception(
                        "There's an endpoint with the same name '{}'.".format(_name)
                    )
                else:
                    return
            if (
                endpoint.route == _endpoint.route
                and endpoint.method == _endpoint.method
            ):
                if not ignore_if_exists and not _endpoint._generated:
                    raise Exception(
                        "There's a method with exactly the same route and method: {} and {}".format(
                            endpoint, _endpoint
                        )
                    )
                else:
                    return
        self._endpoints[name] = endpoint


ENDPOINTS: EndpointsGlobal = EndpointsGlobal()

RE_QUERY_PARAM = re.compile(r"^.*\$\w+/?$")


def print_endpoints():
    # Show a list of endpoints, sorted alphabetically
    if not ENDPOINTS._endpoints:
        logger.info("No endpoints loaded.")
        return

    (_host, _port) = CONFIG.get().server.listen_addr
    addr = "http://{}:{}".format(_host, _port)

    logger.info("\nEndpoints loaded:")

    route_prefix = CONFIG.get().server.api_prefix
    if route_prefix.endswith("/"):
        route_prefix = route_prefix[:-1]

    for _, endpoint in ENDPOINTS._endpoints.items():
        # Force the GET-POST-PUT-DELETE order
        methods = "/".join(
            [
                m
                for m in ("GET", "POST", "PUT", "DELETE")
                if m in endpoint.method.upper()
            ]
        )
        # Replace $param with <param>
        route = re.sub(
            r"\$(\w+)",
            r"<\1>",
            route_prefix + endpoint.route,
        )

        logger.info(
            "    · %s%s (%s)",
            addr,
            route,
            methods,
        )


# This is where the fun at v2
def setup_endpoint(endpoint: EndpointDefinition):
    logger.debug("Setting up endpoint %s %s", endpoint.method, endpoint.route)

    # Check if the query is requesting the logged user's ID
    # If it is and the endpoint does not required authentication,
    # warn that it may be NULL
    logged_user = "$loggedId"
    if logged_user and not endpoint.required_auth:
        logger.warning(
            "The endpoint %s %s uses $loggedId but does not require authentication.\n Keep in mind that the logged user's ID may be NULL.",
            endpoint.method.upper(),
            endpoint.route,
        )

    # Construct the API route taking the prefix into account
    route_prefix = CONFIG.get().server.api_prefix
    if route_prefix.endswith("/"):
        route_prefix = route_prefix[:-1]  # Drop the final /
    full_route = route_prefix + endpoint.route

    # Warn if the pair SQL operation - HTTP verb is not the proper one
    check_method(endpoint.query, endpoint.method, endpoint.route)

    # Warn if the values of auth_required and allowed_roles don't make sense together
    check_auth_roles(
        endpoint.required_auth, endpoint.allowed_roles, endpoint.method, endpoint.route
    )

    # Extract the list of parameters that the user expects to receive
    # in the URL and in the SQL string
    sql_params = extract_params(endpoint.query)
    url_params = extract_params(endpoint.route)

    # Get the required SQL operation
    sql_op = get_sql_op(endpoint.query)

    # If it's a SELECT or a DELETE, make sure that all SQL params can be
    # obtained from the url
    if sql_op in (SQL.SELECT, SQL.DELETE):
        check_params_match(sql_params, url_params, endpoint.route)

    # If it's a SELECT or a DELETE, make sure that all SQL params can be
    # obtained from the url AND the request body
    if sql_op in (SQL.INSERT, SQL.UPDATE):
        check_params_match(
            sql_params, url_params + endpoint.request_body_params, endpoint.route
        )

    # The handler function that will be passed to flask
    def route_handler(*args, **kwargs):
        # Get the user's data from the session token
        logged_user_data = get_logged_user()

        # If this endpoint requires authentication, check that the
        # user is logged in and has the proper role
        if endpoint.required_auth:
            check_session(logged_user_data, endpoint.allowed_roles)

        # Collect all url pattern params
        request_url_params_dict = kwargs

        # If the endpoint requires the logged user's ID, we add it to the available params
        if logged_user:
            request_url_params_dict["loggedId"] = get_current_user_id(logged_user_data)

        # Convert the Silence-style placeholders in the SQL query to proper MySQL placeholders
        query_string = silence_to_mysql(endpoint.query)

        # Default outputs
        res = None
        status = 200

        # SELECT/GET operations
        if sql_op == SQL.SELECT:
            # The URL params have been checked to be enough to fill all SQL params
            url_pattern_params = tuple(
                request_url_params_dict[param] for param in sql_params
            )
            res = dal.api_safe_query(query_string, url_pattern_params)

            # Filter these results according to the URL query string, if there is one
            # Possible TO-DO: do this by directly editing the SQL query for extra efficiency
            res = filter_query_results(res, request.args)

            # In our teaching context, it is safe to assume that if the URL ends
            # with a parameter and we have no results, we should return a 404 code
            if RE_QUERY_PARAM.match(endpoint.route) and not res:
                raise HTTPError(404, "Not found")

        else:  # POST/PUT/DELETE operations
            # Construct a dict for all params expected in the request body, setting them to None if they have not been provided
            form = request.json if request.is_json else request.form

            # TODO: maybe instead of getting putting a none put the default value.
            # SELECT DISTINCT DEFAULT(name) FROM departments
            # take into account that the default value if none is specified is NULL.

            # request_body_params[param] if param in request_body_params else find_default(tabla, columna)

            body_params = {
                param: form.get(param, None) for param in endpoint.request_body_params
            }

            # We have checked that sql_params is a subset of url_params U body_params,
            # construct a joint param object and use it to fill the SQL placeholders
            for param in url_params:
                body_params[param] = request_url_params_dict[param]

            if CONFIG.debug:
                logger.info(
                    log_utils.format_custom_record(
                        "api", "yellow", f"PARAMS {body_params}"
                    )
                )

            # TODO: if the tuple recieves a none, but the database has an explicit default,
            # replace that none with the specific default value.
            param_tuple = tuple(body_params[param] for param in sql_params)

            # print(f"\n\n body paramters:\n {body_params} \n\n request url params dict:\n {request_url_params_dict} \n\n form:\n {form} \n\n param tuple: \n {param_tuple}\n\n query string: \n {query_string}")

            # Run the execute query
            res = dal.api_safe_update(query_string, param_tuple)

        return jsonify(res), status

    # flaskify_url() adapts the URL so that all $variables are converted to Flask-style <variables>
    server_manager.APP.add_url_rule(
        flaskify_url(full_route),
        endpoint.method + endpoint.route,
        route_handler,
        methods=[endpoint.method.value],
    )


# Aux functions


# Extracts the user's data from the session token sent in the header
# Returns a dict with the user's information, or None if the token
# is not present or is invalid
def get_logged_user():
    token = request.headers.get("Token", default=None)
    logged_user_data = None

    if token:
        try:
            logged_user_data = check_token(token)
        except TokenError as exc:
            logger.debug("The user sent an invalid token: %s", str(exc))

    return logged_user_data


# Checks whether the user is logged in and has the proper role
# Raises a 401 HTTP error if the previous conditions are not met
# Note that user_data may be null if the user has not sent a token
# or has sent an invalid one
def check_session(logged_user_data, allowed_roles):
    if logged_user_data is None:
        raise HTTPError(401, "Unauthorized")

    # TODO: CHECK ROLES
    # Check if the user's role is allowed to access this endpoint
    # role_col_name = CONFIG.USER_AUTH_DATA.get("role", None)

    # if role_col_name:  # Only check the role if we know the role column
    #     # Find the role of the user from the user data
    #     user_role = next(
    #         (
    #             v
    #             for k, v in logged_user_data.items()
    #             if k.lower() == role_col_name.lower()
    #         ),
    #         None,
    #     )

    #     logger.debug(
    #         "Allowed roles are %s and the user role is %s",
    #         str(allowed_roles),
    #         user_role,
    #     )

    #     if user_role not in allowed_roles and "*" not in allowed_roles:
    #         raise HTTPError(401, "Unauthorized")


# Return the user's ID if the user is logged in and has a PK, None otherwise
def get_current_user_id(logged_user_data) -> Optional[int]:
    userID = None

    if logged_user_data is not None:
        users_table = CONFIG.get().app.auth.user_auth_table
        match DATABASE_SCHEMA.get_table(users_table):
            case table if table is not None:
                pk = table.primary_key_field
                userID = (
                    logged_user_data[pk] if pk else None
                )  # Returns None if the table has no primary key
            case _:
                pass

    return userID


# Implements filtering, ordering and paging using query strings
def filter_query_results(data, args):
    # Grab all parameters from the query string
    sort_param = args.get("_sort")
    sort_reverse = args.get("_order") == "desc"

    try:
        limit = int(args.get("_limit", None))
    except (ValueError, TypeError):
        limit = None

    try:
        page = int(args.get("_page", None))
    except (ValueError, TypeError):
        page = None

    # Filter, sort and paginate results
    filter_criteria = [pair for pair in args.items() if not pair[0].startswith("_")]
    filter_func = lambda elem: all(
        k not in elem or str(elem[k]).lower() == v.lower() for k, v in filter_criteria
    )
    res = list(filter(filter_func, data))

    def order_key_func(elem):
        v = elem[sort_param]
        return v if v is not None else Min  # Avoids errors when comparing against None

    try:
        res.sort(key=order_key_func, reverse=sort_reverse)
    except KeyError:
        pass

    offset = limit * page if limit and page else 0
    top = offset + limit if limit else len(res)
    return res[offset:top]


# Checks whether the SQL operation and the HTTP verb match
def check_method(sql, verb, endpoint):
    if sql is None:
        return
    sql_op = get_sql_op(sql)

    if sql_op in OP_VERBS:
        correct_verb = OP_VERBS[sql_op]

        if correct_verb != verb.lower():
            # Warn the user about the correct verb to use
            logger.warn(
                f"The '{verb.upper()}' HTTP verb is not correct for the SQL {sql_op.upper()} "
                + f"operation in endpoint {verb.upper()} {endpoint}, the correct verb is {correct_verb.upper()}."
            )
    else:
        # What has the user put here?
        raise Exception(
            f"The SQL query '{sql}' in the endpoint {endpoint} is not supported,"
            + " please use only SELECT/INSERT/UPDATE/DELETE."
        )


def check_auth_roles(auth_required, allowed_roles, method, route):
    # Raise an error if allowed_roles is not a list
    if not isinstance(allowed_roles, list):
        raise Exception(
            f"The value '{allowed_roles}' for the allowed_roles parameter in "
            + f"endpoint {method.upper()} {route} is not allowed, it must be a "
            + "list of allowed roles."
        )

    # Warn if the user has specified some roles but auth_required is false,
    # since it will result in all users having access
    if not auth_required and len(allowed_roles) > 0 and allowed_roles != ["*"]:
        logger.warn(
            f"You have specified allowed roles in endpoint {method.upper()} {route}, "
            + "but auth_required is False. This will result in all users having access "
            + "regardless of their role."
        )

    # Warn if the user has specified an empty list of roles, and auth_required is true,
    # because it will result in noone having access
    if auth_required and len(allowed_roles) == 0:
        logger.warn(
            f"You have set auth_required to True in endpoint {method.upper()} {route}, "
            + "but the list of allowed roles is empty. This will result in noone being able "
            + "to access the endpoint."
        )


# Returns a list of $params in a SQL query or endpoint route,
# without the $'s
def extract_params(string):
    res = re.findall(r"\$\w+", string)
    return [x[1:] for x in res]


# Convers $url_param to <url_param>
def flaskify_url(url):
    return re.sub(r"\$(\w+)", r"<\1>", url)


# Checks whether all SQL params can be filled with the provided params
def check_params_match(sql_params, user_params, route):
    sql_params_set = set(sql_params)
    user_params_set = set(user_params)
    diff = sql_params_set.difference(user_params_set)
    if "loggedId" in diff:
        diff.remove("loggedId")

    if diff:
        params_str = ", ".join(f"${param}" for param in diff)
        raise Exception(
            f"Error creating endpoint {route}: the parameters "
            + f"{params_str} are expected by the SQL query but they are not provided in the URL "
            + "or the request body."
        )
