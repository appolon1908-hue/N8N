#!/usr/bin/env python3
"""Validate roadmap platform packs remain design-only and Middleware-first."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKS_DIR = ROOT / "automations" / "packs"
REQUIRED_PACKS = {
    "codestra.marketing": "codestra-marketing.v2.json",
    "codestra.ai": "codestra-ai.v2.json",
    "codestra.communication": "codestra-communication.v2.json",
    "codestra.social": "codestra-social.v2.json",
}
ROADMAP_KILL_SWITCHES = {
    "LIVE_ADVERTISING_ENABLED",
    "META_READ_SYNC_ENABLED",
    "EXTERNAL_MODEL_CALLS_ENABLED",
    "ENABLE_EXTERNAL_DELIVERY",
    "SOCIAL_READ_SYNC_ENABLED",
    "SOCIAL_PUBLISHING_ENABLED",
    "LIVE_WRITE",
    "ODOO_WRITE",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    packs = {pack["pack"]: pack for pack in (load_json(PACKS_DIR / filename) for filename in REQUIRED_PACKS.values())}

    if set(packs) != set(REQUIRED_PACKS):
        errors.append("roadmap packs missing: " + ", ".join(sorted(set(REQUIRED_PACKS) - set(packs))))

    for pack_name, pack in packs.items():
        if pack.get("active") is not False:
            errors.append(f"{pack_name} must remain inactive")
        workflows = pack.get("workflows")
        if not isinstance(workflows, list) or not workflows:
            errors.append(f"{pack_name} must declare workflows")

    marketing = packs.get("codestra.marketing", {})
    prohibited = set(marketing.get("prohibited_direct_targets") or [])
    for target in ("graph.facebook.com", "googleads.googleapis.com"):
        if target not in prohibited:
            errors.append(f"marketing pack must prohibit direct target {target}")
    if marketing.get("owns_budget_authority") is not False:
        errors.append("marketing pack must not give n8n budget authority")

    ai = packs.get("codestra.ai", {})
    if ai.get("ai_authority") != "advisory-only":
        errors.append("AI pack must declare advisory-only authority")
    for key in ("may_authorize_spend", "may_publish", "may_send_customer_delivery"):
        if ai.get(key) is not False:
            errors.append(f"AI pack must keep {key}=false")
    if ai.get("approval_required_after_ai_output") is not True:
        errors.append("AI pack must require approval after AI output")

    communication = packs.get("codestra.communication", {})
    for key in ("direct_klyrow_access", "direct_telnexa_access"):
        if communication.get(key) is not False:
            errors.append(f"communication pack must keep {key}=false")
    if communication.get("consent_authority") != "communication":
        errors.append("communication pack must own consent decisions outside n8n")

    social = packs.get("codestra.social", {})
    if social.get("canonical_system") != "Codestra Social":
        errors.append("social pack must resolve canonical system name to Codestra Social")
    if social.get("canonical_repository") != "appolon1908-hue/social.codestra.co":
        errors.append("social pack must resolve canonical social repository")
    if social.get("publish_requires_approval") is not True:
        errors.append("social publish workflows must require approval")

    capabilities = load_json(ROOT / "config" / "capabilities.json").get("capabilities", {})
    for flag in ROADMAP_KILL_SWITCHES:
        if capabilities.get(flag) is not False:
            errors.append(f"roadmap kill switch must be false: {flag}")

    if errors:
        print("ROADMAP_PACKS_VALIDATION=FAIL")
        for error in errors:
            print(f"ERROR={error}")
        return 1
    print("ROADMAP_PACKS_VALIDATION=PASS")
    print("ROADMAP_PACKS=4 of 4")
    print("KILL_SWITCHES_ALL_FALSE=YES")
    print("AI_AUTHORITY_ASSERTED_NONE=YES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
