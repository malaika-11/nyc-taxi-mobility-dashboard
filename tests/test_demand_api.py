import unittest

from backend.app import app


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
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_hourly_demand(self):
        response = self.client.get("/api/hourly-demand")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(len(data), 24)
        self.assertEqual(data[0]["hour"], 0)
        self.assertEqual(data[-1]["hour"], 23)
    
    def test_weekday_demand(self):
        response = self.client.get("/api/weekday-average")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 7)
        
    def test_daily_demand(self):
        response = self.client.get("/api/daily-demand")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 31)

    def test_summary(self):
        response = self.client.get("/api/summary")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["busiest_hour"], 18)
        self.assertEqual(data["quietest_hour"], 4)
        self.assertEqual(data["busiest_day"], "Thursday")

if __name__ == "__main__":
    unittest.main()