from typing import List, Optional
from enum import StrEnum
from functools import lru_cache
from re import Pattern

import re

from msgspec import Struct, field


class HttpMethod(StrEnum):
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"


class EndpointDefinition(
    Struct, frozen=True, gc=False, forbid_unknown_fields=True, omit_defaults=True
):
    route: str
    method: HttpMethod
    query: Optional[str]
    description: Optional[str] = field(default=None)
    request_body_params: List[str] = field(default_factory=list)
    required_auth: bool = field(default=False)
    allowed_roles: List[str] = field(default_factory=list)
    _generated: bool = field(default=False)


@lru_cache(maxsize=None, typed=True)
@staticmethod
def regex_path(route: str) -> Pattern:
    pattern = re.sub(r"\$([a-zA-Z_][a-zA-Z0-9_]*)", r"(?P<\1>[^/]+)", route)
    regex_pattern = f"^{pattern}$"
    return re.compile(regex_pattern)
