import unittest

from backend.app import app, get_trip_stats

FULL_DATASET = get_trip_stats().get("trip_count", 0) > 1_000_000

class DemandAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_homepage_loads(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_hourly_demand(self):
        response = self.client.get("/api/hourly-demand")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 24)
        self.assertEqual(data[0]["hour"], 0)
        self.assertEqual(data[-1]["hour"], 23)
    
    def test_weekday_average(self):
        response = self.client.get("/api/weekday-average")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 7)
        self.assertEqual(data[0]["day_of_week"], "Monday")

    def test_boroughs(self):
        data = self.client.get("/api/boroughs").get_json()
        self.assertIn("Manhattan", data)

    @unittest.skipUnless(FULL_DATASET, "full dataset only")
    def test_daily_demand_full(self):
        self.assertEqual(len(self.client.get("/api/daily-demand").get_json()), 31)

    @unittest.skipUnless(FULL_DATASET, "full dataset only")
    def test_summary_full(self):
        data = self.client.get("/api/summary").get_json()

        self.assertEqual(data["busiest_hour"], 18)
        self.assertEqual(data["quietest_hour"], 4)
        self.assertEqual(data["busiest_day"], "Thursday")

    def test_summary_shape(self):
        data = self.client.get("/api/summary").get_json()
        for key in ("total_pickups", "avg_distance", "avg_fare", "busiest_hour", "quietest_hour"):
            self.assertIn(key, data)


class TripsAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def get(self, query=""):
        return self.client.get("/api/trips?limit=20" + query)

    def test_default_page(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertLessEqual(len(body["data"]), 20)
        self.assertGreater(body["total"], 0)

    def test_distance_filter(self):
        rows = self.get("&min_distance=2&max_distance=3").get_json()["data"]
        self.assertTrue(all(2 <= r["trip_distance"] <= 3 for r in rows))

    def test_fare_filter(self):
        rows = self.get("&min_fare=10&max_fare=15").get_json()["data"]
        self.assertTrue(all(10 <= r["fare_amount"] <= 15 for r in rows))

    def test_borough_filter(self):
        rows = self.get("&pickup_borough=Manhattan").get_json()["data"]
        self.assertTrue(all(r["pu_borough"] == "Manhattan" for r in rows))

    def test_sorting(self):
        fares = [r["fare_amount"] for r in self.get("&sort_by=fare&sort_order=desc").get_json()["data"]]
        self.assertEqual(fares, sorted(fares, reverse=True))
        dist = [r["trip_distance"] for r in self.get("&sort_by=distance&sort_order=asc").get_json()["data"]]
        self.assertEqual(dist, sorted(dist))

    def test_date_filter_is_inclusive(self):
        rows = self.get("&start_date=2019-01-10&end_date=2019-01-10").get_json()["data"]
        self.assertTrue(all(r["pickup_datetime"].startswith("2019-01-10") for r in rows))

    def test_bad_input_is_rejected(self):
        self.assertEqual(self.get("&sort_by=nonsense").status_code, 400)
        self.assertEqual(self.get("&sort_order=sideways").status_code, 400)
        self.assertEqual(self.get("&page=0").status_code, 400)
        self.assertEqual(self.client.get("/api/trips?limit=1000").status_code, 400)

    def test_trip_detail(self):
        trip_id = self.get().get_json()["data"][0]["trip_id"]
        body = self.client.get(f"/api/trips/{trip_id}").get_json()
        self.assertEqual(body["trip_id"], trip_id)
        self.assertIn("rate_code", body)
        self.assertEqual(self.client.get("/api/trips/999999999").status_code, 404)


if __name__ == "__main__":
    unittest.main()