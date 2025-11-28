from msgspec import Struct, field


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
    reason: str = field(default="A server error has occurred.")
