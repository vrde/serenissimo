from .. import db
import json

insert = """
    INSERT INTO subscription (user_id, ulss_id, fiscal_code, status_id, last_check, locations)
    VALUES (?, ?, ?, ?, ?, ?)"""

with db.transaction() as t:
    db.init(t)
    db.init_data(t)

for k, v in json.load(open("./db.json")).items():
    with db.transaction() as t:
        sid = db.user.insert(t, k)
        if "ulss" in v and "cf" in v:
            t.execute(
                insert,
                (
                    sid,
                    int(v["ulss"]),
                    v["cf"],
                    v.get("state"),
                    int(v.get("last_check", 0)),
                    json.dumps(v.get("locations")),
                ),
            )
