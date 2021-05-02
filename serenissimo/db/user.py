from .common import select_last_id


def by_id(c, id):
    select = "SELECT * FROM user WHERE id = ?"
    r = c.execute(select, (id,))
    return r.fetchone()


def by_telegram_id(c, telegram_id):
    select = "SELECT * FROM user WHERE telegram_id = ?"
    r = c.execute(select, (telegram_id,))
    return r.fetchone()


def insert(c, telegram_id):
    insert = "INSERT INTO user (telegram_id) VALUES (?)"
    c.execute(insert, (telegram_id,))
    return select_last_id(c)


def delete(c, user_id):
    delete = "DELETE FROM user WHERE id = ?"
    return c.execute(delete, (user_id,))


def select_active(c):
    select = """
        SELECT user.*
        FROM user
            INNER JOIN subscription ON (user.id = subscription.user_id)
        WHERE subscription.ulss_id IS NOT NULL
            AND subscription.fiscal_code IS NOT NULL"""
    return c.execute(select)
