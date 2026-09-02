from __future__ import annotations

import json
from unittest.mock import patch
import unittest

from scripts import policy_n8n


class RuntimeNodeDenylistTests(unittest.TestCase):
    def test_exact_package_inventory_and_provider_examples_are_closed(self) -> None:
        document = json.loads(policy_n8n.RUNTIME_NODE_DENYLIST_PATH.read_text())
        self.assertEqual("n8n-nodes-base", document["package"])
        self.assertEqual("2.32.1", document["version"])
        self.assertEqual(440, len(document["excluded_node_types"]))
        self.assertEqual(441, len(policy_n8n.REQUIRED_RUNTIME_EXCLUDED_NODES))
        for node_type in (
            "n8n-nodes-base.gmail",
            "n8n-nodes-base.googleSheets",
            "n8n-nodes-base.slack",
            "n8n-nodes-base.httpRequest",
        ):
            self.assertIn(node_type, policy_n8n.REQUIRED_RUNTIME_EXCLUDED_NODES)

    def test_inventory_mutation_fails_closed(self) -> None:
        document = json.loads(policy_n8n.RUNTIME_NODE_DENYLIST_PATH.read_text())
        document["excluded_node_types"][0] = "n8n-nodes-base.unreviewed"
        with patch.object(
            policy_n8n.RUNTIME_NODE_DENYLIST_PATH.__class__,
            "read_text",
            return_value=json.dumps(document),
        ):
            with self.assertRaisesRegex(ValueError, "reviewed package inventory"):
                policy_n8n.load_runtime_node_denylist()

    def test_non_string_inventory_fails_without_type_error(self) -> None:
        document = json.loads(policy_n8n.RUNTIME_NODE_DENYLIST_PATH.read_text())
        document["excluded_node_types"][0] = {}
        with patch.object(
            policy_n8n.RUNTIME_NODE_DENYLIST_PATH.__class__,
            "read_text",
            return_value=json.dumps(document),
        ):
            with self.assertRaisesRegex(ValueError, "440 unique string"):
                policy_n8n.load_runtime_node_denylist()


if __name__ == "__main__":
    unittest.main()
