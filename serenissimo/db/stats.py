def select(c):
    count_vaccinated = """
        SELECT COUNT(*) as vaccinated
        FROM log
        WHERE name = 'vaccinated'"""
    count_users = """
        SELECT COUNT(*) as users
        FROM user
            INNER JOIN subscription ON (user.id = subscription.user_id)
        WHERE ulss_id IS NOT NULL
            AND fiscal_code IS NOT NULL"""
    return {
        "vaccinated": c.execute(count_vaccinated).fetchone()["vaccinated"],
        "users": c.execute(count_users).fetchone()["users"],
    }
