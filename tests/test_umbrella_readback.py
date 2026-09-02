from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts.readback_umbrella_controls import CONTROL_NAMES, main, read_controls


class UmbrellaReadbackTests(unittest.TestCase):
    def test_exact_false_controls_pass(self) -> None:
        controls, missing, non_false = read_controls(
            [*(f"{name}=false" for name in CONTROL_NAMES), "UNRELATED_SETTING=redacted"]
        )
        self.assertEqual({name: False for name in CONTROL_NAMES}, controls)
        self.assertEqual([], missing)
        self.assertEqual([], non_false)

    def test_missing_is_not_false(self) -> None:
        controls, missing, non_false = read_controls([])
        self.assertEqual({name: None for name in CONTROL_NAMES}, controls)
        self.assertEqual(list(CONTROL_NAMES), missing)
        self.assertEqual([], non_false)

    def test_true_malformed_and_duplicate_values_fail(self) -> None:
        entries = [f"{name}=false" for name in CONTROL_NAMES]
        entries[0] = f"{CONTROL_NAMES[0]}=true"
        entries[1] = f"{CONTROL_NAMES[1]}=FALSE"
        entries.append(f"{CONTROL_NAMES[2]}=false")
        controls, missing, non_false = read_controls(entries)
        self.assertEqual([], missing)
        self.assertEqual(
            [CONTROL_NAMES[0], CONTROL_NAMES[1], CONTROL_NAMES[2]], non_false
        )
        self.assertIs(controls[CONTROL_NAMES[0]], True)
        self.assertIsNone(controls[CONTROL_NAMES[1]])
        self.assertIsNone(controls[CONTROL_NAMES[2]])

    def test_inspection_launch_failures_remain_machine_readable(self) -> None:
        failures = (
            OSError("docker unavailable"),
            subprocess.TimeoutExpired(["docker", "inspect"], 15),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                output = io.StringIO()
                with (
                    patch(
                        "scripts.readback_umbrella_controls.subprocess.run",
                        side_effect=failure,
                    ),
                    patch.object(sys, "argv", ["readback", "n8n-test"]),
                    redirect_stdout(output),
                ):
                    result = main()
                payload = json.loads(output.getvalue())
                self.assertEqual(1, result)
                self.assertIs(payload["pass"], False)
                self.assertEqual(list(CONTROL_NAMES), payload["missing"])
                self.assertEqual(
                    "container inspection unavailable", payload["error"]
                )


if __name__ == "__main__":
    unittest.main()
