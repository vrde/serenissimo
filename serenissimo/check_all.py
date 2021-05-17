from time import sleep
from serenissimo import agent, db

SELECT_ALL_SUBSCRIPTIONS = """SELECT user.id as user_id,
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
  INNER JOIN status ON (status.id = subscription.status_id)
WHERE status_id NOT IN ("already_booked", "already_vaccinated")
  --AND subscription.ulss_id = 6
  AND subscription.ulss_id IS NOT NULL
  AND subscription.fiscal_code IS NOT NULL
  AND subscription.health_insurance_number IS NOT NULL"""

with db.connection() as c:
    for s in c.execute(SELECT_ALL_SUBSCRIPTIONS):
        ulss_id = s["ulss_id"]
        fiscal_code = s["fiscal_code"]
        health_insurance_number = s["health_insurance_number"]
        status_id, available, unavailable = agent.check(
            ulss_id, fiscal_code, health_insurance_number
        )
        print(f"{ulss_id} {fiscal_code} {health_insurance_number} {status_id}")
        print("Available locations:")
        print(agent.format_locations(available))
        print("Unavailable locations:")
        print(agent.format_locations(unavailable))
        print()
        sleep(0)
