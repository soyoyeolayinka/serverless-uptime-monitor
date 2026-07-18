import os, sys, unittest
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.modules["boto3"] = MagicMock()
import app

class MonitorTests(unittest.TestCase):
    @patch("app.urllib.request.urlopen")
    def test_healthy_endpoint(self, urlopen):
        response = MagicMock(status=200)
        urlopen.return_value.__enter__.return_value = response
        result = app.check_endpoint({"name": "web", "url": "https://example.com", "expected_status": 200, "max_latency_ms": 5000})
        self.assertTrue(result["healthy"])
        self.assertEqual(result["status_code"], 200)
    @patch("app.urllib.request.urlopen", side_effect=TimeoutError())
    def test_timeout_is_unhealthy(self, _urlopen):
        result = app.check_endpoint({"name": "web", "url": "https://example.com"})
        self.assertFalse(result["healthy"])
        self.assertEqual(result["status_code"], 0)

if __name__ == "__main__": unittest.main()
