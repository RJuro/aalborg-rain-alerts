from datetime import datetime, timezone, timedelta
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from backend import BackendError
from tests.test_backend import forecast

class AppTests(unittest.TestCase):
    def test_forecast_and_disabled_signup_render(self):
        data = forecast()
        data.update(expected_rain_mm=0,current_temperature_c=12)
        with patch("backend.fetch_weather",return_value=data):
            app = AppTest.from_file("../app.py").run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.text_input),1)
        self.assertTrue(next(button for button in app.button if "Send me" in button.label).disabled)

    def test_submitting_without_consent_shows_error(self):
        data = forecast()
        data.update(expected_rain_mm=0,current_temperature_c=12)
        with patch.dict("os.environ",{"SUBSCRIPTIONS_ENABLED":"true"}), patch("backend.fetch_weather",return_value=data):
            app = AppTest.from_file("../app.py").run(timeout=20)
            app.text_input[0].set_value("student@example.com")
            next(button for button in app.button if "Send me" in button.label).click()
            app.run()
        self.assertFalse(app.exception)
        self.assertIn("Please agree",app.error[0].value)

    def test_submitting_valid_signup_shows_confirmation_receipt(self):
        data = forecast()
        data.update(expected_rain_mm=0,current_temperature_c=12)
        with patch.dict("os.environ",{"SUBSCRIPTIONS_ENABLED":"true"}), patch("backend.fetch_weather",return_value=data), patch("backend.subscribe",return_value="Check your inbox for a confirmation link.") as send:
            app = AppTest.from_file("../app.py").run(timeout=20)
            app.text_input[0].set_value("student@example.com")
            app.checkbox[0].check()
            next(button for button in app.button if "Send me" in button.label).click()
            app.run()
        self.assertFalse(app.exception)
        self.assertIn("confirmation",app.success[0].value)
        send.assert_called_once()

if __name__ == "__main__":
    unittest.main()
