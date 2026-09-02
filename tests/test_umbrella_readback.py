from __future__ import annotations

import unittest

from scripts.readback_umbrella_controls import CONTROL_NAMES, read_controls


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
        self.assertIsNone(controls[CONTROL_NAMES[2]])


if __name__ == "__main__":
    unittest.main()
