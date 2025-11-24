# Silence
# Copyright (C) 2025 Oscar Alvarez Gonzalez

from typing import Tuple, Literal, List

import os

from msgspec import Struct, field, toml, MsgspecError

_CONFIG_FILE_PATH: Literal["config.toml"] = "config.toml"


class Base(Struct, frozen=True, gc=False, forbid_unknown_fields=True):
    pass


class General(
    Base,
    frozen=True,
    gc=False,
):
    auto_endpoints: bool = field(default=True)
    endpoint_statistics: bool = field(default=True)
    display_endpoints_on_start: bool = field(default=True)
    colored_output: bool = field(default=True)
    default_template: Tuple[str, str] = field(default=("IISSI-US", "employees"))
    check_latest_version: bool = field(default=True)


class Server(Base, frozen=True, gc=False):
    listen_addr: Tuple[str, int] = field(default=("127.0.0.1", 8080))
    http_cache_time: int = field(default=0)
    api_prefix: str = field(default="/api")
    serve_api: bool = field(default=True)
    serve_static_files: bool = field(default=True)
    summary_endpoint: bool = field(default=False)


"""By default, passwords, roles (e.g. admin or whether the user is active) and tokens will be stored in their own tables"""


class Auth(Base, frozen=True, gc=False):
    enable: bool = field(default=True)
    """(table_name, column) will be used as the identifier field for user authentication"""
    user_auth_table: str = field(default="users")
    user_auth_field: str = field(default="email")
    max_token_age: int = 86400
    # chech_user_is_active: bool # DEPRECATED
    # secret_key: str # DEPRECATED
    allow_signup: bool = field(default=True)


class App(Base, frozen=True, gc=False):
    auth: Auth = field(default_factory=Auth)
    admin_panel: bool = field(default=True)


class DbConn(Base, frozen=True, gc=False):
    host: Tuple[str, int] = field(default=("127.0.0.1", 3306))
    username: str = field(default="default_username")
    password: str = field(default="default_password")
    db: str = field(default="default_db")
    bootstrap_scripts: List[str] = field(default_factory=list)


class Config(Base, frozen=True, gc=False):
    general: General = field(default_factory=General)
    server: Server = field(default_factory=Server)
    app: App = field(default_factory=App)
    db_conn: DbConn = field(default_factory=DbConn)


# Maybe the 'config.toml' path should be a program's argument...
def _load_config() -> Config:
    try:
        with open(_CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            return toml.decode(f.read(), type=Config)
    except Exception as e:
        match e:
            case FileNotFoundError() as e:
                raise ConfigError(
                    "Cannot find the config.toml file at {}/{}! "
                    "Check whether you're running Silence from the project's root folder. "
                    "{}".format(os.getcwd(), _CONFIG_FILE_PATH, e)
                )
            case MsgspecError() as e:
                raise ConfigError(
                    "There was an error while trying to serialize the config file. "
                    "Ensure that it is correcly formatted. "
                    "{}".format(e)
                )


def _load_default_config() -> Config:
    return Config()


class ConfigError(Exception):
    pass
