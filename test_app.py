import unittest
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