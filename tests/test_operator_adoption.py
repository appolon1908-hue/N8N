from __future__ import annotations

from copy import deepcopy

from scripts.validate_operator_adoption import load_manifest, validate_manifest


def test_current_operator_adoption_manifest_is_source_only() -> None:
    assert validate_manifest(load_manifest()) == []


def test_runtime_or_effect_authorization_fails_closed() -> None:
    document = deepcopy(load_manifest())
    document["runtimeApplied"] = True
    document["productionPromotionAuthorized"] = True
    document["workflowActivationAuthorized"] = True
    document["externalEffectsAuthorized"] = True

    errors = validate_manifest(document)

    assert any("runtimeApplied" in error for error in errors)
    assert any("productionPromotionAuthorized" in error for error in errors)
    assert any("workflowActivationAuthorized" in error for error in errors)
    assert any("externalEffectsAuthorized" in error for error in errors)


def test_unverified_domain_and_dependencies_cannot_be_promoted_in_source() -> None:
    document = deepcopy(load_manifest())
    document["domainStatus"] = "VERIFIED"
    document["dependencies"][0]["status"] = "VERIFIED"

    errors = validate_manifest(document)

    assert any("domainStatus" in error for error in errors)
    assert any("dependency Keycloak must remain UNVERIFIED" in error for error in errors)


def test_required_native_security_controls_cannot_be_removed() -> None:
    document = deepcopy(load_manifest())
    document["requirements"]["nativeCsrfAndSessionControlsPreserved"] = False
    document["securityInvariants"] = [
        item
        for item in document["securityInvariants"]
        if "workflow credentials" not in item.lower()
    ]

    errors = validate_manifest(document)

    assert any("requirements differ" in error for error in errors)
    assert any("workflow credentials" in error for error in errors)
