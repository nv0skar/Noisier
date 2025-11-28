from silence.server import endpoint_setup as server_endpoint
from silence.__main__ import CONFIG
from silence.exceptions import ServerError

from os.path import join
from os import getcwd

import asyncio
import sys

from granian.server.embed import Server
from granian.rsgi import Scope
from granian._granian import RSGIHTTPProtocol

from msgspec import json


static_folder = (
    join(getcwd(), "static") if CONFIG.get().server.serve_static_files else None
)

(JSON_ENCODER, JSON_DECODER) = (json.Encoder(), json.Decoder())

UNKNOWN_ROUTE = ServerError(404, "Unknown route.")


async def app(scope: Scope, proto: RSGIHTTPProtocol):
    assert scope.proto == "http"
    route_prefix = CONFIG.get().server.api_prefix

    if route_prefix.endswith("/"):
        route_prefix = route_prefix[:-1]

    # Route this to the API endpoints façade
    if scope.path.startswith(route_prefix):
        path = scope.path[len(route_prefix) :]  # Strip API prefix
        if not path.startswith("/"):
            path = "/" + path
        print(server_endpoint.ENDPOINTS.find_matching_route(path))
        print(path)
        pass

    proto.response_str(
        status=UNKNOWN_ROUTE.code,
        headers=[("content-type", "text/json")],
        body=JSON_ENCODER.encode(UNKNOWN_ROUTE).decode("utf-8"),
    )


def server_instance():
    return Server(app, port=CONFIG.get().server.listen_addr[1])


def serve():
    event_loop = asyncio.new_event_loop()

    server_task = event_loop.create_task(server_instance().serve())
    try:
        event_loop.run_until_complete(server_task)
    except KeyboardInterrupt:
        sys.exit()
