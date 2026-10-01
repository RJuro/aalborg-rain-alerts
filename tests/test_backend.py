import copy
from datetime import datetime, timezone, timedelta
import unittest
from unittest.mock import Mock, patch
import requests
from backend import BackendError, fetch_weather, normalize_email, subscribe

def forecast():
    now = datetime.now(timezone.utc)
    return {
        "city":"Aalborg","fetched_at":now.isoformat(),"rain_likely":False,
        "max_hourly_probability":20,"threshold_percent":60,"minimum_rain_mm":0.2,
        "horizon_hours":6,"cooldown_hours":6,"first_rain_start":None,
        "hours":[{"start":now.isoformat(),"end":(now+timedelta(hours=1)).isoformat(),"probability":20,"rain_mm":0} for _ in range(24)]
    }

def response(data, status=200):
    result = Mock(status_code=status, ok=200 <= status < 300)
    result.json.return_value = data
    return result

class ClientTests(unittest.TestCase):
    def test_email_normalization(self):
        self.assertEqual(normalize_email("  Student+rain@Example.COM "), "student+rain@example.com")

    def test_multiple_recipients_and_header_injection_are_rejected(self):
        for address in ("one@example.com,two@example.com", "a@example.com\nBcc:x@example.com", "missing", "@example.com"):
            with self.subTest(address=address), self.assertRaises(BackendError):
                normalize_email(address)

    @patch("backend.requests.request")
    def test_fresh_weather_is_accepted(self, request):
        request.return_value = response(forecast())
        self.assertEqual(len(fetch_weather()["hours"]), 24)
        self.assertTrue(request.call_args.args[1].endswith("/webhook/aalborg-weather-v1"))

    @patch("backend.requests.request")
    def test_stale_forecast_is_rejected(self, request):
        data = forecast()
        data["fetched_at"] = (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
        request.return_value = response(data)
        with self.assertRaises(BackendError):
            fetch_weather()

    @patch("backend.requests.request")
    def test_incomplete_and_invalid_weather_are_rejected(self, request):
        for modify in (
            lambda x: x.pop("hours"),
            lambda x: x.update(max_hourly_probability=101),
            lambda x: x.update(rain_likely="false"),
            lambda x: x.update(rain_likely=True,first_rain_start=None),
            lambda x: x.update(fetched_at="2026-01-01T12:00:00"),
        ):
            data = forecast()
            modify(data)
            request.return_value = response(data)
            with self.assertRaises(BackendError):
                fetch_weather()

    @patch("backend.requests.request")
    def test_network_errors_do_not_expose_backend_details(self, request):
        request.side_effect = requests.ConnectionError("secret upstream detail")
        with self.assertRaises(BackendError) as caught:
            fetch_weather()
        self.assertNotIn("secret", str(caught.exception))

    @patch("backend.requests.request")
    def test_signup_uses_distinct_secure_tokens_and_consent(self, request):
        request.return_value = response({"ok":True,"message":"Check inbox"},202)
        self.assertEqual(subscribe(" Student@EXAMPLE.com ",True),"Check inbox")
        payload = request.call_args.kwargs["json"]
        self.assertEqual(payload["email"],"student@example.com")
        self.assertTrue(payload["consent"])
        self.assertEqual(len(payload["confirm_token"]),43)
        self.assertEqual(len(payload["unsubscribe_token"]),43)
        self.assertNotEqual(payload["confirm_token"],payload["unsubscribe_token"])

    @patch("backend.requests.request")
    def test_missing_consent_never_calls_backend(self, request):
        with self.assertRaises(BackendError):
            subscribe("student@example.com",False)
        request.assert_not_called()

    @patch("backend.requests.request")
    def test_backend_failure_does_not_claim_success(self, request):
        request.return_value = response({"ok":False},500)
        with self.assertRaises(BackendError):
            subscribe("student@example.com",True)

if __name__ == "__main__":
    unittest.main()
