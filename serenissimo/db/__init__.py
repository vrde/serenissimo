# https://charlesleifer.com/blog/going-fast-with-sqlite-and-python/
# https://www.skoumal.com/en/parallel-read-and-write-in-sqlite/
# https://docs.oracle.com/database/bdb181/html/bdb-sql/lockhandling.html

import sqlite3
from contextlib import contextmanager
from . import user, subscription, log, stats
import pkg_resources


import logging

logger = logging.getLogger()


@contextmanager
def transaction(database="db.sqlite"):
    # We must issue a "BEGIN IMMEDIATE" explicitly when running in auto-commit mode.
    c = connect(database)
    c.execute("BEGIN IMMEDIATE")
    try:
        yield c
    except:
        c.rollback()
        raise
    else:
        c.commit()
    finally:
        c.close()


@contextmanager
def connection(database="db.sqlite"):
    c = connect(database)
    try:
        yield c
    except:
        raise
    finally:
        c.close()


def dict_factory(c, row):
    d = {}
    for idx, col in enumerate(c.description):
        d[col[0]] = row[idx]
    return d


total = 0


def tracer(id):
    global total
    i = total
    total += 1

    def trace(statement):
        print("\n".join("{}: {}".format(id, t) for t in statement.split("\n")))
        print()

    return trace


def connect(database="db.sqlite"):
    c = sqlite3.connect(database, isolation_level=None)
    c.execute("PRAGMA foreign_keys = ON")
    c.execute("PRAGMA journal_mode = wal")
    c.row_factory = dict_factory
    # c.set_trace_callback(tracer(i))
    return c


def init(c):
    script = pkg_resources.resource_string(__name__, "tables.sql")
    c.executescript(script.decode("utf8"))


def init_data(c):
    script = pkg_resources.resource_string(__name__, "data.sql")
    c.executescript(script.decode("utf8"))
