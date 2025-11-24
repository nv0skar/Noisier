from silence.auth.tokens import create_token
from silence.db import dal
from silence.sql.builder import get_login_query, get_register_user_query
from silence.__main__ import CONFIG
from silence.exceptions import HTTPError
from silence.logging.default_logger import logger
from silence.logging import utils as log_utils

from flask import jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from silence.sql.tables import DATABASE_SCHEMA

# Defines the default endpoints provided by Silence,
# mainly /login and /register


def login():
    USERS_TABLE, IDENTIFIER_FIELD, PASSWORD_FIELD, ROLE_FIELD, ACTIVE_FIELD = (
        get_login_settings()
    )
    # Ensure that the user has sent the required fields
    form = request.json if request.is_json else request.form
    form = filter_fields_db(form, USERS_TABLE)

    username = form.get(IDENTIFIER_FIELD, None)
    password = form.get(PASSWORD_FIELD, None)

    if not username or not password:
        raise HTTPError(
            400, f"Both '{IDENTIFIER_FIELD}' and '{PASSWORD_FIELD}' are required"
        )

    logger.debug("Login request from user %s", username)

    # Look if there is an user with such username
    q = get_login_query(USERS_TABLE, IDENTIFIER_FIELD, username)
    users = dal.api_safe_query(q)

    if not users:
        logger.debug("The identifier %s was not found", username)
        raise HTTPError(400, "The user or the password are not correct")

    # The identifier field should be unique (/register also takes care of that)
    # so we can just extract the first one
    user = users[0]

    # Check if the user's password matches the provided one
    if PASSWORD_FIELD not in user:
        raise HTTPError(500, f"The user has no attribute '{PASSWORD_FIELD}'")

    password_ok = check_password_hash(user[PASSWORD_FIELD], password)
    if not password_ok:
        logger.debug("Incorrect password")
        raise HTTPError(400, "The user or the password are not correct")

    # If a column has been specified for the "is active" field, and the check
    # is enabled in the settings, check that the user has not been deactivated
    if ACTIVE_FIELD is not None:
        if not user[ACTIVE_FIELD]:
            logger.debug("The user is deactivated, login denied")
            raise HTTPError(401, "This user has been deactivated")

    # If we've reached here the login is successful, generate a session token
    # and return it with the logged user's info
    logger.debug("Login OK")

    if CONFIG.debug:
        logger.info(log_utils.format_custom_record("api", "yellow", f"PARAMS {form}"))

    token = create_token(user)
    del user[PASSWORD_FIELD]
    res = {"sessionToken": token, "user": user}
    return jsonify(res), 200


def register():
    USERS_TABLE, IDENTIFIER_FIELD, PASSWORD_FIELD, ROLE_FIELD, ACTIVE_FIELD = (
        get_login_settings()
    )

    # Ensure that the user has sent the required fields
    form = request.json if request.is_json else request.form
    form = filter_fields_db(form, USERS_TABLE)

    username = form.get(IDENTIFIER_FIELD, None)
    password = form.get(PASSWORD_FIELD, None)

    if not username or not password:
        raise HTTPError(
            400, f"Both '{IDENTIFIER_FIELD}' and '{PASSWORD_FIELD}' are required"
        )

    # Do not log the submitted password
    form_debug = form.copy()
    del form_debug[PASSWORD_FIELD]
    logger.debug(f"Register request with data {form_debug}")

    # Ensure that the identifier is unique
    login_q = get_login_query(USERS_TABLE, IDENTIFIER_FIELD, username)
    other_users = dal.api_safe_query(login_q)

    if other_users:
        logger.debug("The identifier %s already exists", username)
        raise HTTPError(
            400, f"There already exists another user with that {IDENTIFIER_FIELD}"
        )

    # Create the user object, replacing the password with the hashed one
    user = dict(form)
    user[PASSWORD_FIELD] = generate_password_hash(password)

    # Assign a default active status, if the activity check is on and none has
    # been provided
    # if ACTIVE_FIELD and ACTIVE_FIELD not in user:
    #     user[ACTIVE_FIELD] = CONFIG.DEFAULT_ACTIVE_STATUS

    # Try to insert it in the DB
    # Since the /register endpoint must adapt to any possible table,
    # we assume that the user knows what they're doing and submits the
    # appropriate fields. Otherwise, the DB will just complain.
    register_q = get_register_user_query(USERS_TABLE, user)
    dal.api_safe_update(register_q)

    # Fetch the newly created user from the DB (some fields may have been)
    # automatically generated, like its ID
    # It should now exist
    user = dal.api_safe_query(login_q)[0]

    # If we've reached here the register is successful, generate a session token
    # and return it with the logged user's info
    logger.debug("Register OK")

    if CONFIG.debug:
        logger.info(log_utils.format_custom_record("api", "yellow", f"PARAMS {form}"))

    token = create_token(user)
    del user[PASSWORD_FIELD]
    res = {"sessionToken": token, "user": user}
    return jsonify(res), 200


###############################################################################
# Aux functions


# Transforms the received dict of fields into a filtered one that shares
# the same capitalization with the DB columns
def filter_fields_db(data, table_name):
    cols = DATABASE_SCHEMA.get_table(table_name)
    assert cols is not None
    res = {}

    for field, value in data.items():
        for col in cols.fields:
            if field.casefold() == col.name.casefold():
                res[col.name] = value

    return res


# Returns a given column name with the correct capitalization for its table
# Raises a ValueError if it can't be found in the given table
def col_correct_case(col_name, table_name):
    cols = DATABASE_SCHEMA.get_table(table_name)
    assert cols is not None

    for col in cols.fields:
        if col.name.casefold() == col_name.casefold():
            return col

    raise ValueError(f"The column {col_name} could not be found in table {table_name}")


# Returns the login table and fields as specified in the settings,
# with the correct capitalization to avoid SQL errors
def get_login_settings():
    users_table = CONFIG.get().app.auth.user_auth_table
    identifier_field = col_correct_case(
        CONFIG.get().app.auth.user_auth_field, users_table
    )
    password_field = col_correct_case("password", users_table)

    # if "role" in CONFIG.USER_AUTH_DATA:
    #     role_field = col_correct_case(CONFIG.USER_AUTH_DATA["role"], users_table)
    # else:
    #     role_field = None

    # if "active_status" in CONFIG.USER_AUTH_DATA:
    #     active_field = col_correct_case(
    #         CONFIG.USER_AUTH_DATA["active_status"], users_table
    #     )
    # else:
    #     active_field = None

    return users_table, identifier_field, password_field, "", ""
