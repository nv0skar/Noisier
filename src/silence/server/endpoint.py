from typing import List, Optional, Tuple
from enum import StrEnum

from msgspec import Struct, field


class HttpMethod(StrEnum):
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"


"""
To achieve near constant time pattern matching, is assumed that paterns are
always at the end of the route, they are always integers and the last
part of a static route must contain characters.
"""


class RoutePattern(Struct, forbid_unknown_fields=True, omit_defaults=True):
    url_parts: Tuple[str, ...] = field(default_factory=tuple)
    method: HttpMethod = field(default=HttpMethod.GET)
    parameterized: bool = field(default=False)
    parameter_name: Optional[str] = field(default=None)

    @staticmethod
    def new_from_parser(route: str, method: HttpMethod) -> RoutePattern:
        parts: Tuple[str, ...] = tuple(
            part.casefold() for part in route.split("/") if part != ""
        )
        if len(parts) == 0:
            return RoutePattern(tuple(), method, False, None)
        match "$" in parts[-1]:
            case True:
                return RoutePattern(parts[:-1], method, True, parts[-1])
            case False:
                return RoutePattern(parts, method, False, None)

    @staticmethod
    def new_from_request(
        route: str, method: HttpMethod
    ) -> Tuple[RoutePattern, Optional[int]]:
        parts: Tuple[str, ...] = tuple(
            part.casefold() for part in route.split("/") if part != ""
        )
        """
        Decide whether the route is parameterized or not by checking
        if the final part can be serialized an an integer
        """
        if len(parts) == 0:
            return (RoutePattern(tuple(), method, False, None), None)
        match parts[-1].isnumeric():
            case True:
                return (RoutePattern(parts[:-1], method, True, None), int(parts[-1]))
            case False:
                return (RoutePattern(parts, method, False, None), None)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, RoutePattern):
            raise Exception()
        return (
            self.url_parts == value.url_parts
            and self.method == value.method
            and self.parameterized == value.parameterized
        )


class EndpointDefinition(Struct, forbid_unknown_fields=True, omit_defaults=True):
    route: str
    method: HttpMethod
    query: Optional[str]
    description: Optional[str] = field(default=None)
    request_body_params: List[str] = field(default_factory=list)
    required_auth: bool = field(default=False)
    allowed_roles: List[str] = field(default_factory=list)
    _generated: bool = field(default=False)


class EndpointWithValue(
    Struct, frozen=True, forbid_unknown_fields=True, omit_defaults=True
):
    endpoint: EndpointDefinition
    param_value: Optional[int]
