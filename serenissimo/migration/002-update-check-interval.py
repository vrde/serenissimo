from serenissimo import db

MIGRATION = """
UPDATE status
SET update_interval = (SELECT 30 * 60)
WHERE id = 'eligible' OR id = 'maybe_eligible';
"""

with db.transaction() as t:
    t.executescript(MIGRATION)
