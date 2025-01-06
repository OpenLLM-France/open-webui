import logging
from contextvars import ContextVar

from open_webui.env import SRC_LOG_LEVELS
from peewee import *
from peewee import InterfaceError as PeeWeeInterfaceError
from peewee import PostgresqlDatabase
from playhouse.db_url import connect, parse
from playhouse.shortcuts import ReconnectMixin
from psycopg2 import connect as psycopg2_connect
from psycopg2.errors import DuplicateDatabase
from urllib.parse import urlparse


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])

db_state_default = {"closed": None, "conn": None, "ctx": None, "transactions": None}
db_state = ContextVar("db_state", default=db_state_default.copy())


class PeeweeConnectionState(object):
    def __init__(self, **kwargs):
        super().__setattr__("_state", db_state)
        super().__init__(**kwargs)

    def __setattr__(self, name, value):
        self._state.get()[name] = value

    def __getattr__(self, name):
        value = self._state.get()[name]
        return value


class CustomReconnectMixin(ReconnectMixin):
    reconnect_errors = (
        # psycopg2
        (OperationalError, "termin"),
        (InterfaceError, "closed"),
        # peewee
        (PeeWeeInterfaceError, "closed"),
    )


class ReconnectingPostgresqlDatabase(CustomReconnectMixin, PostgresqlDatabase):
    pass


def create_database_if_not_exists(db_url):
    # Parse the database URL to extract details
    parsed_url = urlparse(db_url)
    database = parsed_url.path.lstrip("/")
    user = parsed_url.username
    password = parsed_url.password
    host = parsed_url.hostname
    port = parsed_url.port or 5432

    try:
        # Connect to the default "postgres" database
        conn = psycopg2_connect(
            dbname="postgres",
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.autocommit = True
        with conn.cursor() as cursor:
            # Attempt to create the database
            cursor.execute(f"CREATE DATABASE {database}")
            log.info(f"Database '{database}' created successfully.")
    except DuplicateDatabase:
        log.info(f"Database '{database}' already exists.")
    except Exception as e:
        log.error(f"Failed to create database '{database}': {e}")
        raise


def register_connection(db_url):
    create_database_if_not_exists(db_url)
    db = connect(db_url, unquote_password=True)
    if isinstance(db, PostgresqlDatabase):
        # Enable autoconnect for SQLite databases, managed by Peewee
        db.autoconnect = True
        db.reuse_if_open = True
        log.info("Connected to PostgreSQL database")
        # Get the connection details
        connection = parse(db_url, unquote_password=True)

        # Use our custom database class that supports reconnection
        db = ReconnectingPostgresqlDatabase(**connection)
        db.connect(reuse_if_open=True)
    elif isinstance(db, SqliteDatabase):
        # Enable autoconnect for SQLite databases, managed by Peewee
        db.autoconnect = True
        db.reuse_if_open = True
        log.info("Connected to SQLite database")
    else:
        raise ValueError("Unsupported database connection")
    return db
