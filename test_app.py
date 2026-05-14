import os
import unittest

# Import must not open a MySQL connection on the Jenkins host (DB_HOST "db" is Docker-only).
os.environ["SKIP_DB_AT_IMPORT"] = "1"

from application import application

class TestApp(unittest.TestCase):

    def setUp(self):
        self.client = application.test_client()

    def test_home(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_login_page(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()