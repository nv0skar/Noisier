from msgspec import Struct


class DatabaseError(Exception):
    pass


# A SQL string may not be correct
class SQLWarning(Warning):
    pass


# Generic warnings for endpoint creation
class EndpointWarning(Warning):
    pass


# Generic errors for endpoint creation
class EndpointError(Exception):
    pass


# Errors for checking session tokens
class TokenError(Exception):
    pass


class ServerError(Struct, frozen=True):
    code: int
    reason: str


class ServerErrorWrapper(Exception):
    __slots__ = ["_error"]

    _error: ServerError

    def __init__(self, error: ServerError):
        self._error = error
