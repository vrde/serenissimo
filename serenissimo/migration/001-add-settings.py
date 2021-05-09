from serenissimo import db

MIGRATION = """
ALTER TABLE user ADD COLUMN snooze_from INTEGER;
ALTER TABLE user ADD COLUMN snooze_to INTEGER;
"""

with db.transaction() as t:
    t.executescript(MIGRATION)
