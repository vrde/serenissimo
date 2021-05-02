from .common import select_last_id


def insert(c, name, x=None, y=None, z=None):
    insert = "INSERT INTO log (name, x, y, z) VALUES (?, ?, ?, ?)"
    c.execute(
        insert,
        (name, x, y, z),
    )
    return select_last_id(c)
