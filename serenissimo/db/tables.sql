CREATE TABLE IF NOT EXISTS user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_id TEXT,
  ts DATETIME DEFAULT (CAST(strftime('%s', 'now') AS INT)),
  last_message DATETIME,
  snooze_from INTEGER,
  snooze_to INTEGER
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_telegram_id ON user(telegram_id);
CREATE TABLE IF NOT EXISTS subscription (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  ulss_id INTEGER,
  status_id TEXT NOT NULL DEFAULT 'unknown',
  fiscal_code TEXT NULL,
  health_insurance_number TEXT NULL,
  locations TEXT NOT NULL DEFAULT 'null',
  last_check DATETIME DEFAULT 0,
  ts DATETIME DEFAULT (CAST(strftime('%s', 'now') AS INT)),
  FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
  FOREIGN KEY (ulss_id) REFERENCES ulss (id),
  FOREIGN KEY (status_id) REFERENCES status (id)
);
CREATE INDEX IF NOT EXISTS idx_subscription_status_id ON subscription(status_id);
CREATE INDEX IF NOT EXISTS idx_subscription_last_check ON subscription(last_check);
CREATE TABLE IF NOT EXISTS ulss (
  id INTEGER NOT NULL PRIMARY KEY,
  name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS status (
  id TEXT NOT NULL PRIMARY KEY,
  update_interval INTEGER
);
CREATE TABLE IF NOT EXISTS log (
  name TEXT NOT NULL,
  x TEXT NULL,
  y TEXT NULL,
  z TEXT NULL,
  ts DATETIME DEFAULT (CAST(strftime('%s', 'now') AS INT))
);
CREATE INDEX IF NOT EXISTS idx_log_name ON log(name);
--
--
-- Views
--
DROP VIEW IF EXISTS view_stale_subscriptions;
CREATE VIEW IF NOT EXISTS view_stale_subscriptions AS
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
  INNER JOIN status ON (status.id = subscription.status_id)
WHERE status_id NOT IN ("already_booked", "already_vaccinated")
  AND subscription.ulss_id IS NOT NULL
  AND subscription.fiscal_code IS NOT NULL
  AND subscription.health_insurance_number IS NOT NULL
  AND subscription.last_check <= CAST(strftime('%s', 'now') AS INT) - status.update_interval
  AND (
    (
      -- The user has not set snooze time
      user.snooze_from IS NULL
      AND user.snooze_to IS NULL
    )
    OR (
      -- If the user as set snooze time, check it
      -- (and adjust to the correct timezone)
      strftime('%H', datetime('now', '+2 hours')) NOT BETWEEN user.snooze_from AND user.snooze_to
    )
  )
ORDER BY subscription.last_check ASC;