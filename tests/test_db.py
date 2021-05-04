import unittest
import sqlite3
from serenissimo import db

FC1 = "XXXXXXXXXXXXXXX1"
FC2 = "XXXXXXXXXXXXXXX2"
FC3 = "XXXXXXXXXXXXXXX3"
FC4 = "XXXXXXXXXXXXXXX4"
FC5 = "XXXXXXXXXXXXXXX5"
FC6 = "XXXXXXXXXXXXXXX6"
FC7 = "XXXXXXXXXXXXXXX7"
FC8 = "XXXXXXXXXXXXXXX8"
FC9 = "XXXXXXXXXXXXXXX9"

HN1 = "111111"
HN2 = "222222"
HN3 = "333333"
HN4 = "444444"
HN5 = "555555"
HN6 = "666666"
HN7 = "777777"
HN8 = "888888"
HN9 = "999999"


class TestDB(unittest.TestCase):
    def setUp(self):
        self.c = db.connect(":memory:")
        db.init(self.c)
        db.init_data(self.c)

    def test_init(self):
        r = self.c.execute("SELECT COUNT(*) as total FROM ulss")
        self.assertEqual(r.fetchone()["total"], 9)

        r = self.c.execute("SELECT COUNT(*) as total FROM status")
        self.assertEqual(r.fetchone()["total"], 7)

    def test_insert_user(self):
        user_id = db.user.insert(self.c, "1234")

        r = self.c.execute("SELECT * FROM user WHERE id = ?", (user_id,))
        s = r.fetchone()

        self.assertEqual(s["id"], user_id)
        self.assertEqual(s["telegram_id"], "1234")
        self.assertTrue(s["ts"])

        with self.assertRaises(sqlite3.IntegrityError):
            db.user.insert(self.c, "1234")

    def test_get_user_by_telegram_id(self):
        user_id = db.user.insert(self.c, "1234")
        self.assertEqual(db.user.by_telegram_id(self.c, "1234")["id"], user_id)

    def test_get_user_does_not_exist(self):
        self.assertIsNone(db.user.by_id(self.c, "1234"))

    def test_insert_subscription(self):
        user_id = db.user.insert(self.c, "1234")
        db.subscription.insert(self.c, user_id)

        r = self.c.execute("SELECT * FROM subscription WHERE user_id = ?", (user_id,))
        l = r.fetchall()
        self.assertEqual(len(l), 1)
        s = l[0]
        subscription_id = s["id"]

        self.assertIsNone(s["ulss_id"])
        self.assertIsNone(s["fiscal_code"])
        self.assertEqual(s["status_id"], "unknown")
        self.assertIsNone(s["health_insurance_number"])
        self.assertEqual(s["locations"], "null")
        self.assertEqual(s["last_check"], 0)

    def test_update_subscription(self):
        user_id = db.user.insert(self.c, "1234")
        subscription_id = db.subscription.insert(self.c, user_id)
        db.subscription.update(self.c, subscription_id, ulss_id=1)

        r = self.c.execute("SELECT * FROM subscription WHERE user_id = ?", (user_id,))
        l = r.fetchall()
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0]["ulss_id"], 1)
        self.assertIsNone(l[0]["fiscal_code"])

    def test_insert_subscription_fail_for_non_existent_ulss(self):
        user_id = db.user.insert(self.c, "1234")
        with self.assertRaises(sqlite3.IntegrityError):
            db.subscription.insert(self.c, user_id, 0, "XXXXXXXXXXXXXXXX")

    def test_delete_user(self):
        user_id = db.user.insert(self.c, "1234")

        db.subscription.insert(self.c, user_id, ulss_id=1, fiscal_code=FC1)
        db.subscription.insert(self.c, user_id, ulss_id=2, fiscal_code=FC2)
        db.subscription.insert(self.c, user_id, ulss_id=3, fiscal_code=FC3)

        db.user.delete(self.c, user_id)
        r = self.c.execute("SELECT * FROM subscription WHERE user_id = ?", (user_id,))
        l = r.fetchall()
        self.assertEqual(len(l), 0)
        # Should not raise
        db.user.delete(self.c, user_id)

    def test_delete_user_is_null(self):
        db.user.delete(self.c, None)

    def test_select_subscriptions(self):
        user_id = db.user.insert(self.c, "1234")
        user_id2 = db.user.insert(self.c, "5678")

        db.subscription.insert(self.c, user_id, ulss_id=1, fiscal_code=FC1)
        db.subscription.insert(self.c, user_id2, ulss_id=4, fiscal_code=FC1)
        db.subscription.insert(self.c, user_id, ulss_id=2, fiscal_code=FC2)
        db.subscription.insert(self.c, user_id2, ulss_id=5, fiscal_code=FC1)
        db.subscription.insert(self.c, user_id, ulss_id=3, fiscal_code=FC3)

        r = db.subscription.by_user(self.c, user_id)
        l = r.fetchall()
        self.assertEqual(l[0]["id"], 1)
        self.assertEqual(l[0]["ulss_id"], 1)
        self.assertEqual(l[0]["fiscal_code"], FC1)
        self.assertEqual(l[0]["user_id"], user_id)
        self.assertEqual(l[1]["id"], 3)
        self.assertEqual(l[1]["ulss_id"], 2)
        self.assertEqual(l[1]["fiscal_code"], FC2)
        self.assertEqual(l[1]["user_id"], user_id)
        self.assertEqual(l[2]["id"], 5)
        self.assertEqual(l[2]["ulss_id"], 3)
        self.assertEqual(l[2]["fiscal_code"], FC3)
        self.assertEqual(l[2]["user_id"], user_id)

        r = db.subscription.by_user(self.c, user_id2)
        l = r.fetchall()
        self.assertEqual(len(l), 2)
        self.assertEqual(l[0]["id"], 2)
        self.assertEqual(l[0]["ulss_id"], 4)
        self.assertEqual(l[0]["fiscal_code"], FC1)
        self.assertEqual(l[0]["user_id"], user_id2)
        self.assertEqual(l[1]["id"], 4)
        self.assertEqual(l[1]["ulss_id"], 5)
        self.assertEqual(l[1]["fiscal_code"], FC1)
        self.assertEqual(l[1]["user_id"], user_id2)

    def test_select_last_subscription(self):
        user_id = db.user.insert(self.c, "1234")
        user_id2 = db.user.insert(self.c, "5678")

        db.subscription.insert(self.c, user_id, ulss_id=1, fiscal_code=FC1)
        db.subscription.insert(self.c, user_id, ulss_id=2, fiscal_code=FC2)
        db.subscription.insert(self.c, user_id, ulss_id=3, fiscal_code=FC3)

        last = db.subscription.last_by_user(self.c, user_id)

        self.assertEqual(last["id"], 3)
        self.assertEqual(last["ulss_id"], 3)
        self.assertEqual(last["fiscal_code"], FC3)
        self.assertEqual(last["user_id"], user_id)

    def test_select_active_subscriptions(self):
        alice = db.user.insert(self.c, "1234")
        bob = db.user.insert(self.c, "5678")
        carol = db.user.insert(self.c, "9012")

        now = self.c.execute(
            "SELECT CAST(strftime('%s', 'now') AS INT) as now"
        ).fetchone()["now"]
        one_hour_ago = now - 60 * 60
        six_hour_ago = now - 6 * 60 * 60
        one_day_ago = now - 24 * 60 * 60

        insert = """
            INSERT INTO subscription (user_id, ulss_id, fiscal_code, health_insurance_number, status_id, last_check)
            VALUES (?, ?, ?, ?, ?, ?)"""

        self.c.executemany(
            insert,
            [
                # Yep
                [alice, 1, FC1, HN1, "unknown", 0],
                # Yep
                [alice, 1, FC2, HN2, "eligible", one_hour_ago],
                # Nope
                [bob, 1, FC3, HN3, "eligible", now],
                # Nope
                [bob, 1, FC4, HN4, "not_eligible", one_hour_ago],
                # Yep
                [bob, 1, FC5, HN5, "not_registered", one_day_ago],
                # Yep
                [carol, 1, FC6, HN6, "maybe_eligible", six_hour_ago],
                # Nope
                [carol, 1, FC7, HN7, "maybe_eligible", now],
                # Nope
                [carol, 1, FC8, HN8, "maybe_eligible", now],
                # Nope
                [carol, 1, FC9, HN9, "already_vaccinated", six_hour_ago],
            ],
        )

        to_check = db.subscription.select_stale(self.c).fetchall()

        self.assertEqual(
            to_check,
            [
                {
                    "user_id": 1,
                    "subscription_id": 1,
                    "telegram_id": "1234",
                    "ulss_id": 1,
                    "fiscal_code": "XXXXXXXXXXXXXXX1",
                    "health_insurance_number": HN1,
                    "status_id": "unknown",
                    "last_check": 0,
                    "locations": "null",
                },
                {
                    "user_id": 1,
                    "subscription_id": 2,
                    "telegram_id": "1234",
                    "ulss_id": 1,
                    "fiscal_code": "XXXXXXXXXXXXXXX2",
                    "health_insurance_number": HN2,
                    "status_id": "eligible",
                    "last_check": one_hour_ago,
                    "locations": "null",
                },
                {
                    "user_id": 2,
                    "subscription_id": 5,
                    "telegram_id": "5678",
                    "fiscal_code": "XXXXXXXXXXXXXXX5",
                    "health_insurance_number": HN5,
                    "ulss_id": 1,
                    "status_id": "not_registered",
                    "last_check": one_day_ago,
                    "locations": "null",
                },
                {
                    "user_id": 3,
                    "subscription_id": 6,
                    "telegram_id": "9012",
                    "fiscal_code": "XXXXXXXXXXXXXXX6",
                    "health_insurance_number": HN6,
                    "ulss_id": 1,
                    "status_id": "maybe_eligible",
                    "last_check": six_hour_ago,
                    "locations": "null",
                },
            ],
        )

    def test_log(self):
        db.log.insert(self.c, "vaccinated")
        db.log.insert(self.c, "vaccinated")
        db.log.insert(self.c, "vaccinated")
        r = self.c.execute("SELECT * FROM log")
        l = r.fetchall()
        self.assertEqual(len(l), 3)


if __name__ == "__main__":
    unittest.main()
