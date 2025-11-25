from typing import List, Optional
from enum import StrEnum

from msgspec import Struct, field


class HttpMethod(StrEnum):
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"


class EndpointDefinition(
    Struct, gc=False, forbid_unknown_fields=True, omit_defaults=True
):
    route: str
    method: HttpMethod
    query: Optional[str]
    description: Optional[str] = field(default=None)
    request_body_params: List[str] = field(default_factory=list)
    required_auth: bool = field(default=False)
    allowed_roles: List[str] = field(default_factory=list)
    _generated: bool = field(default=False)
