"""Offline regression checks for the pinned client and dashboard data contract."""

import json
import logging
import sys
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from http import HTTPMethod
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lambda_function import DashboardCloudClient, LaMarzoccoDashboard, extract_statistics
from pylamarzocco.const import CUSTOMER_APP_URL
from pylamarzocco.models import ThingStatistics


def statistics_payload():
    # Midnight in Los Angeles, including a date that is already tomorrow in UTC.
    timestamp = 1789110000000
    shots = [
        {
            "time": timestamp + i * 60_000,
            "extractionSeconds": 28.95 + i,
            "doseMode": "MassType",
            "doseIndex": "DoseA",
            "doseValue": 36.25 + i,
            "targetTemperature": 95,
        }
        for i in range(8)
    ]
    return {
        "serialNumber": "test-machine",
        "selectedWidgets": [
            {"code": "LAST_COFFEE", "index": 1, "output": {"lastCoffees": shots}},
            {
                "code": "COFFEE_AND_FLUSH_COUNTER",
                "index": 1,
                "output": {"totalCoffee": 5664, "totalFlush": 2169},
            },
            {
                "code": "COFFEE_AND_FLUSH_TREND",
                "index": 1,
                "output": {
                    "days": 7,
                    "timezone": "America/Los_Angeles",
                    "coffees": [{"timestamp": timestamp, "value": 2}],
                    "flushes": [{"timestamp": timestamp, "value": 1}],
                },
            },
        ],
    }


def extract(payload):
    return extract_statistics(ThingStatistics.from_dict(deepcopy(payload)), payload)


class StatisticsTests(unittest.TestCase):
    def test_lifetime_counts_are_not_replaced_by_weekly_counts(self):
        result = extract(statistics_payload())
        self.assertEqual((result["total_shots"], result["total_flushes"]), (5664, 2169))
        self.assertEqual(result["usage_trend"]["total_shots"], 2)
        self.assertEqual(result["usage_trend"]["total_flushes"], 1)

    def test_preserves_weights_targets_and_newest_five(self):
        payload = statistics_payload()
        result = extract(payload)
        self.assertEqual(len(result["recent_shots"]), 5)
        latest = result["recent_shots"][0]
        self.assertEqual(latest["time"], payload["selectedWidgets"][0]["output"]["lastCoffees"][-1]["time"])
        self.assertEqual(latest["dose_value"], 43.2)
        self.assertEqual(latest["target_temperature_f"], 203.0)
        self.assertEqual(latest["dose_mode"], "MassType")
        json.dumps(result, allow_nan=False)

    def test_searches_past_missing_and_invalid_weights_and_keeps_zero(self):
        payload = statistics_payload()
        shots = payload["selectedWidgets"][0]["output"]["lastCoffees"]
        shots[-1]["doseValue"] = None
        shots[-2]["doseValue"] = float("nan")
        shots[-3]["doseValue"] = 0
        result = extract(payload)
        self.assertEqual(len(result["recent_shots"]), 5)
        self.assertEqual(result["recent_shots"][0]["dose_value"], 0)
        json.dumps(result, allow_nan=False)

    def test_uses_machine_timezone_for_daily_dates(self):
        payload = statistics_payload()
        trend = payload["selectedWidgets"][2]["output"]
        timestamp = int(datetime(2026, 9, 12, 1, tzinfo=timezone.utc).timestamp() * 1000)
        for key in ("coffees", "flushes"):
            trend[key][0]["timestamp"] = timestamp
        self.assertEqual(extract(payload)["usage_trend"]["daily"][0]["date"], "2026-09-11")

    def test_zero_lifetime_counts_are_valid(self):
        payload = statistics_payload()
        payload["selectedWidgets"][1]["output"] = {"totalCoffee": 0, "totalFlush": 0}
        self.assertEqual(extract(payload)["total_shots"], 0)

    def test_missing_counter_fails_instead_of_publishing_zero(self):
        payload = statistics_payload()
        del payload["selectedWidgets"][1]
        with self.assertRaisesRegex(ValueError, "Lifetime"):
            extract(payload)

    def test_optional_recent_shots_and_trend_may_be_absent(self):
        payload = statistics_payload()
        payload["selectedWidgets"] = [payload["selectedWidgets"][1]]
        result = extract(payload)
        self.assertEqual(result["recent_shots"], [])
        self.assertIsNone(result["usage_trend"])


class ClientAndCollectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_client_keeps_raw_fields_omitted_by_models(self):
        payload = statistics_payload()
        client = object.__new__(DashboardCloudClient)
        client._rest_api_call = AsyncMock(return_value=deepcopy(payload))
        parsed = await client.get_thing_statistics("test-machine")
        client._rest_api_call.assert_awaited_once_with(
            url=f"{CUSTOMER_APP_URL}/things/test-machine/stats", method=HTTPMethod.GET
        )
        self.assertEqual(client.statistics_payload, payload)
        self.assertEqual(extract_statistics(parsed, client.statistics_payload)["total_shots"], 5664)

    async def test_collection_and_html_preserve_new_information(self):
        payload = statistics_payload()
        dashboard = object.__new__(LaMarzoccoDashboard)
        dashboard.get_credentials = AsyncMock(return_value={"username": "test", "password": "test"})
        dashboard.get_or_create_installation_key = AsyncMock(return_value=object())
        thing = SimpleNamespace(
            name="Test Machine", serial_number="test-machine", model_name="Linea Mini",
            connected=True, connection_date="2026-09-11T12:00:00+00:00", image_url="",
            require_firmware_update=False, available_firmware_update=False,
        )
        client = SimpleNamespace(list_things=AsyncMock(return_value=[thing]), statistics_payload=payload)
        machine = SimpleNamespace(
            get_dashboard=AsyncMock(), get_settings=AsyncMock(), get_schedule=AsyncMock(),
            get_statistics=AsyncMock(), statistics=ThingStatistics.from_dict(deepcopy(payload)),
            to_dict=lambda: {
                "dashboard": {"widgets": []},
                "settings": {"firmwares": {"Gateway": {
                    "build_version": "v1", "change_log": "<script>example</script>\nStandby fix"
                }}},
                "schedule": {
                    "smart_stand_by": {"enabled": True, "minutes": 10},
                    "smart_wake_up_sleep": {"smart_stand_by_enabled": False, "smart_stand_by_minutes": 0},
                },
            },
        )
        with patch("lambda_function.DashboardCloudClient", return_value=client), patch(
            "pylamarzocco.LaMarzoccoMachine", return_value=machine
        ):
            data = await dashboard.collect_machine_data()
        self.assertEqual(data["client_version"], "2.4.3")
        self.assertEqual(data["settings"]["smart_standby_minutes"], 10)
        self.assertTrue(data["settings"]["smart_standby_enabled"])
        self.assertEqual(data["statistics"]["total_shots"], 5664)
        html = dashboard.generate_dashboard_html(data)
        self.assertIn("Past 7 Days", html)
        self.assertIn("Brew target 203.0", html)
        self.assertIn("Shot 5", html)
        self.assertIn("&lt;script&gt;example&lt;/script&gt;", html)
        self.assertIn("Gateway v1 release notes", html)
        self.assertNotIn("<script>example</script>", html)

        data["recent_shots"] = data["recent_shots"][:2]
        data["usage_trend"] = None
        html = dashboard.generate_dashboard_html(data)
        self.assertIn("Average (Last 2)", html)
        self.assertNotIn("Past 7 Days", html)

        machine.get_statistics.side_effect = ValueError("bad statistics")
        with patch("lambda_function.DashboardCloudClient", return_value=client), patch(
            "pylamarzocco.LaMarzoccoMachine", return_value=machine
        ), self.assertRaisesRegex(ValueError, "bad statistics"):
            await dashboard.collect_machine_data()

    async def test_collection_failure_does_not_overwrite_published_files(self):
        dashboard = object.__new__(LaMarzoccoDashboard)
        dashboard.collect_machine_data = AsyncMock(side_effect=ValueError("bad statistics"))
        dashboard.upload_to_s3 = AsyncMock()
        dashboard.invalidate_cloudfront = AsyncMock()
        response = await dashboard.run()
        self.assertEqual(response["statusCode"], 500)
        dashboard.upload_to_s3.assert_not_awaited()
        dashboard.invalidate_cloudfront.assert_not_awaited()


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    unittest.main()
