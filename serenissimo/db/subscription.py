from .common import select_last_id


def insert(c, user_id, ulss_id=None, fiscal_code=None, health_insurance_number=None):
    # This is a bot, so users insert fields incrementally. We ask for the ULSS
    # first, then the fiscal_code, so there can be only one "incomplete"
    # subscription.
    insert = """
        INSERT INTO subscription (user_id, ulss_id, fiscal_code, health_insurance_number)
        VALUES (?, ?, ?, ?)"""
    c.execute(insert, (user_id, ulss_id, fiscal_code, health_insurance_number))
    return select_last_id(c)


def update(
    c,
    id,
    ulss_id=None,
    fiscal_code=None,
    health_insurance_number=None,
    status_id=None,
    locations=None,
    set_last_check=False,
):
    update = """
        UPDATE
            subscription
        SET
            ulss_id = coalesce(:ulss_id, ulss_id),
            fiscal_code = coalesce(:fiscal_code, fiscal_code),
            health_insurance_number = coalesce(:health_insurance_number, health_insurance_number),
            status_id = coalesce(:status_id, status_id),
            locations = coalesce(:locations, locations),
            last_check = (SELECT CASE WHEN :set_last_check THEN CAST(strftime('%s', 'now') AS INT) ELSE last_check END)

        WHERE id = :id"""

    return c.execute(
        update,
        {
            "id": id,
            "ulss_id": ulss_id,
            "fiscal_code": fiscal_code,
            "health_insurance_number": health_insurance_number,
            "status_id": status_id,
            "locations": locations,
            "set_last_check": set_last_check,
        },
    )


def delete(c, subscription_id):
    delete = """DELETE FROM subscription WHERE subscription_id = ?"""
    return c.execute(delete, (subscription_id,))


def by_user(c, user_id):
    select = "SELECT * FROM subscription WHERE user_id = ? ORDER BY id ASC"
    return c.execute(select, (user_id,))


def last_by_user(c, user_id):
    select = """
        SELECT *
        FROM subscription
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1"""
    return c.execute(select, (user_id,)).fetchone()


def by_id(c, subscription_id):
    select = """
        SELECT user.id as user_id,
            user.telegram_id,
            subscription.id as subscription_id,
            subscription.ulss_id,
            subscription.fiscal_code,
            subscription.health_insurance_number,
            subscription.status_id,
            subscription.last_check,
            subscription.locations

        FROM user
            INNER JOIN subscription ON (user.id = subscription.user_id)
            LEFT JOIN status ON (status.id = subscription.status_id)

        WHERE subscription.id = ?"""
    return c.execute(select, (subscription_id,)).fetchone()


def select_stale(c):
    select = "SELECT * FROM view_stale_subscriptions"
    return c.execute(select)