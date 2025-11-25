from silence.__main__ import CONFIG
from silence.server import endpoint_setup as server_endpoint, manager as server_manager
from silence.server.endpoint import EndpointDefinition, HttpMethod
from msgspec import json


# Instantiate the endpoint on the server
def load_endpoints():
    for _, endpoint_def in server_endpoint.ENDPOINTS._endpoints.items():
        match endpoint_def._generated:
            case True if (
                CONFIG.get().general.auto_endpoints and endpoint_def.query is not None
            ):
                server_endpoint.setup_endpoint(endpoint_def)
            case False if endpoint_def.query is not None:
                server_endpoint.setup_endpoint(endpoint_def)
            case _:
                pass


# TODO: REGISTER AUTH ENDPOINTS
# Register the Silence-provided endpoints
def load_default_endpoints():
    from silence.server import default_endpoints

    route_prefix = CONFIG.get().server.api_prefix
    if route_prefix.endswith("/"):
        route_prefix = route_prefix[:-1]

    if CONFIG.get().server.summary_endpoint:
        server_endpoint.ENDPOINTS.put(
            "_generated_summary",
            EndpointDefinition(
                "",
                HttpMethod.GET,
                description="Returns the data regarding the API endpoints",
                query=None,
            ),
        )

        server_manager.APP.add_url_rule(
            route_prefix, "APITree", show_api_endpoints, methods=["GET"]
        )

    if CONFIG.get().app.auth.enable:
        login_route = f"{route_prefix}/login"
        # server_manager.API_SUMMARY.register_endpoint(
        #     {
        #         "route": login_route,
        #         "method": "POST",
        #         "desc": "Starts a new session, returning a session token and the user data if the login is successful",
        #     }
        # )
        server_manager.APP.add_url_rule(
            login_route, "login", default_endpoints.login, methods=["POST"]
        )

    if CONFIG.get().app.auth.allow_signup:
        register_route = f"{route_prefix}/register"
        # server_manager.API_SUMMARY.register_endpoint(
        #     {
        #         "route": register_route,
        #         "method": "POST",
        #         "desc": "Creates a new user, returning a session token and the user data if the register is successful",
        #     }
        # )
        server_manager.APP.add_url_rule(
            register_route, "register", default_endpoints.register, methods=["POST"]
        )


def show_api_endpoints():
    return json.encode(server_endpoint.ENDPOINTS._endpoints), 200
