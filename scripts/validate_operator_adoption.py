#!/usr/bin/env python3
"""Validate the protected n8n operator theme/SSO adoption contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "orbit" / "adoption-manifest.json"

EXPECTED_TOP_LEVEL = {
    "schemaVersion": "2.1.0",
    "status": "SOURCE_ONLY_NO_GO",
    "repository": "appolon1908-hue/N8N",
    "targetBranch": "main",
    "surfaceId": "codestra-n8n-operator",
    "classification": "protected-vendor-operator-ui",
    "adoptionMode": "supported-operator-theme-and-sso",
    "domain": "n8n.codestra.agency",
    "domainStatus": "UNVERIFIED",
    "runtimeApplied": False,
    "productionPromotionAuthorized": False,
    "workflowActivationAuthorized": False,
    "externalEffectsAuthorized": False,
}

EXPECTED_REQUIREMENTS = {
    "canonicalCodestraIdentity": True,
    "authorizationCodePkceForInteractiveUsers": True,
    "realLogoutAndSessionRevocation": True,
    "logoutAll": True,
    "browserTokenStorageProhibited": True,
    "nativeN8nProjectsAndPermissionsPreserved": True,
    "nativeCsrfAndSessionControlsPreserved": True,
    "nativeCredentialEncryptionPreserved": True,
    "supportedThemeOrExtensionPointsOnly": True,
    "sharedCustomerHeaderFooter": False,
    "publicCustomerAccess": False,
    "operatorRbac": True,
    "audit": True,
    "monitoring": True,
    "upgradeCompatibility": True,
    "backupRestoreAndRollback": True,
}

EXPECTED_DEPENDENCIES = {
    "Keycloak",
    "Caddy and Kong",
    "SDK-repository",
    "Infustruction-repo",
}

REQUIRED_INVARIANT_MARKERS = {
    "fork upstream n8n core",
    "workflow credentials",
    "native project",
    "browser local storage",
    "public customer surface",
    "activate workflows or external effects",
}

REQUIRED_EVIDENCE_MARKERS = {
    "DNS, TLS, ingress",
    "Keycloak client",
    "operator roles",
    "session-expired",
    "dangerous-node exclusions",
    "upgrade compatibility",
    "monitoring and audit",
    "backup, isolated restore",
    "exact source SHA",
    "independent approval",
}


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("operator adoption manifest must be a JSON object")
    return value


def _string_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        errors.append(f"{label} must be a non-empty list")
        return []
    if any(not isinstance(item, str) or not item.strip() for item in value):
        errors.append(f"{label} must contain non-empty strings only")
        return []
    items = [item.strip() for item in value]
    if len(set(items)) != len(items):
        errors.append(f"{label} contains duplicate entries")
    return items


def validate_manifest(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for field, expected in EXPECTED_TOP_LEVEL.items():
        if document.get(field) != expected:
            errors.append(f"{field} must remain {expected!r}")

    requirements = document.get("requirements")
    if requirements != EXPECTED_REQUIREMENTS:
        errors.append("requirements differ from the reviewed operator safety contract")

    invariants = _string_list(document.get("securityInvariants"), "securityInvariants", errors)
    invariant_text = "\n".join(invariants).lower()
    for marker in sorted(REQUIRED_INVARIANT_MARKERS):
        if marker.lower() not in invariant_text:
            errors.append(f"securityInvariants lacks required marker: {marker}")

    evidence = _string_list(
        document.get("requiredEvidenceBeforeRuntimeGo"),
        "requiredEvidenceBeforeRuntimeGo",
        errors,
    )
    evidence_text = "\n".join(evidence).lower()
    for marker in sorted(REQUIRED_EVIDENCE_MARKERS):
        if marker.lower() not in evidence_text:
            errors.append(f"requiredEvidenceBeforeRuntimeGo lacks marker: {marker}")

    dependencies = document.get("dependencies")
    if not isinstance(dependencies, list) or any(not isinstance(row, dict) for row in dependencies):
        errors.append("dependencies must be a list of objects")
    else:
        authorities = [row.get("authority") for row in dependencies]
        if set(authorities) != EXPECTED_DEPENDENCIES or len(authorities) != len(EXPECTED_DEPENDENCIES):
            errors.append("dependency authorities differ from the reviewed set")
        for row in dependencies:
            authority = row.get("authority", "UNKNOWN")
            if row.get("status") != "UNVERIFIED":
                errors.append(f"dependency {authority} must remain UNVERIFIED")
            if not isinstance(row.get("purpose"), str) or not row["purpose"].strip():
                errors.append(f"dependency {authority} lacks a purpose")

    return errors


def main() -> int:
    try:
        document = load_manifest()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print("OPERATOR_ADOPTION=FAIL")
        print(f"ERROR={exc}")
        return 1

    errors = validate_manifest(document)
    if errors:
        print("OPERATOR_ADOPTION=FAIL")
        for error in errors:
            print(f"ERROR={error}")
        return 1

    print("OPERATOR_ADOPTION=PASS")
    print("STATUS=SOURCE_ONLY_NO_GO")
    print("DOMAIN_STATUS=UNVERIFIED")
    print("RUNTIME_APPLIED=false")
    print("PRODUCTION_PROMOTION_AUTHORIZED=false")
    print("WORKFLOW_ACTIVATION_AUTHORIZED=false")
    print("EXTERNAL_EFFECTS_AUTHORIZED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
