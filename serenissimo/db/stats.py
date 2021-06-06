def select(c):
    count_booked = """
        SELECT COUNT(*) as booked
        FROM log
        WHERE name = 'booked' AND x = 1"""
    count_incomplete = """
        SELECT COUNT(*) as users
        FROM user
            INNER JOIN subscription ON (user.id = subscription.user_id)
        WHERE ulss_id IS NOT NULL
            AND fiscal_code IS NOT NULL
            AND health_insurance_number IS NULL
            """
    count_users = """
        SELECT COUNT(*) as users
        FROM user
            INNER JOIN subscription ON (user.id = subscription.user_id)
        WHERE ulss_id IS NOT NULL
            AND fiscal_code IS NOT NULL
            AND health_insurance_number IS NOT NULL
            """
    return {
        "booked": c.execute(count_booked).fetchone()["booked"],
        "users": c.execute(count_users).fetchone()["users"],
        "users_incomplete": c.execute(count_incomplete).fetchone()["users"],
    }


def group_subscribers_by_day(c):
    select = """
        WITH RECURSIVE days(day) AS (
        SELECT 0
        UNION ALL
        SELECT day -1
        FROM days
        WHERE day > -14
        )
        SELECT days.day,
        coalesce(vals.total, 0)
        FROM days
        LEFT OUTER JOIN (
            SELECT CAST(
                (
                julianday(date(user.ts, 'unixepoch')) - julianday('now')
                ) AS INTEGER
            ) as day,
            count(*) as total
            FROM user
            join subscription on user.id = subscription.user_id
            WHERE fiscal_code IS NOT NULL
            AND ulss_id IS NOT NULL
            AND health_insurance_number IS NOT NULL
            AND user.ts > strftime('%s', date('now', '-14 days'))
            GROUP BY date(user.ts, 'unixepoch')
        ) AS vals ON (days.day = vals.day)
    """

    return c.execute(select).fetchall()


def group_notifications_by_day(c):
    select = """
        WITH RECURSIVE days(day) AS (
            SELECT 0
            UNION ALL
            SELECT day -1
            FROM days
            WHERE day > -14
        )
        SELECT days.day,
        coalesce(vals.total, 0)
        FROM days
        LEFT OUTER JOIN (
            SELECT CAST(
                (
                    julianday(date(ts, 'unixepoch')) - julianday('now')
                ) AS INTEGER
            ) as day,
            count(*) as total
            FROM log
            WHERE ts > strftime('%s', date('now', '-14 days'))
            AND name IN ("notification")
            GROUP BY date(ts, 'unixepoch')
        ) AS vals ON (days.day = vals.day)
        """

    return c.execute(select).fetchall()


def group_errors_by_day(c):
    select = """
        WITH RECURSIVE days(day) AS (
            SELECT 0
            UNION ALL
            SELECT day -1
            FROM days
            WHERE day > -14
        )
        SELECT days.day,
        coalesce(vals.total, 0)
        FROM days
        LEFT OUTER JOIN (
            SELECT CAST(
                (
                    julianday(date(ts, 'unixepoch')) - julianday('now')
                ) AS INTEGER
            ) as day,
            count(*) as total
            FROM log
            WHERE ts > strftime('%s', date('now', '-14 days'))
            AND name IN ("http-error", "application-error")
            GROUP BY date(ts, 'unixepoch')
        ) AS vals ON (days.day = vals.day)
    """

    return c.execute(select).fetchall()
