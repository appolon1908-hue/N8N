from __future__ import annotations

import unittest
from copy import deepcopy

from scripts.validate_operator_adoption import load_manifest, validate_manifest


class OperatorAdoptionTests(unittest.TestCase):
    def test_current_operator_adoption_manifest_is_source_only(self) -> None:
        self.assertEqual(validate_manifest(load_manifest()), [])

    def test_runtime_or_effect_authorization_fails_closed(self) -> None:
        document = deepcopy(load_manifest())
        document["runtimeApplied"] = True
        document["productionPromotionAuthorized"] = True
        document["workflowActivationAuthorized"] = True
        document["externalEffectsAuthorized"] = True

        errors = validate_manifest(document)

        self.assertTrue(any("runtimeApplied" in error for error in errors))
        self.assertTrue(any("productionPromotionAuthorized" in error for error in errors))
        self.assertTrue(any("workflowActivationAuthorized" in error for error in errors))
        self.assertTrue(any("externalEffectsAuthorized" in error for error in errors))

    def test_unverified_domain_and_dependencies_cannot_be_promoted_in_source(self) -> None:
        document = deepcopy(load_manifest())
        document["domainStatus"] = "VERIFIED"
        document["dependencies"][0]["status"] = "VERIFIED"

        errors = validate_manifest(document)

        self.assertTrue(any("domainStatus" in error for error in errors))
        self.assertTrue(
            any("dependency Keycloak must remain UNVERIFIED" in error for error in errors)
        )

    def test_required_native_security_controls_cannot_be_removed(self) -> None:
        document = deepcopy(load_manifest())
        document["requirements"]["nativeCsrfAndSessionControlsPreserved"] = False
        document["securityInvariants"] = [
            item
            for item in document["securityInvariants"]
            if "workflow credentials" not in item.lower()
        ]

        errors = validate_manifest(document)

        self.assertTrue(any("requirements differ" in error for error in errors))
        self.assertTrue(any("workflow credentials" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
