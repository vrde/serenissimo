def select(c):
    count_vaccinated = """
        SELECT COUNT(*) as vaccinated
        FROM log
        WHERE name = 'vaccinated'"""
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
        "vaccinated": c.execute(count_vaccinated).fetchone()["vaccinated"],
        "users": c.execute(count_users).fetchone()["users"],
        "users_incomplete": c.execute(count_incomplete).fetchone()["users"],
    }
