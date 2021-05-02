def select_last_id(c):
    select = "SELECT last_insert_rowid() AS id"
    return c.execute(select).fetchone()["id"]
