#!/usr/bin/env python3
"""Record a verified n8n binding policy from real verification artifacts.

`config/n8n-policy.json` is an attestation, not configuration. Flipping it to
VERIFIED asserts that two named people checked a real deployment and that
evidence exists for the endpoint, egress, credential, and editor bindings.

This tool exists so that attestation can only be produced from artifacts that
actually exist. Every evidence hash is computed from a file on disk; none can be
supplied as a literal. If an artifact is missing or empty, the run fails and the
policy is left untouched. The result is re-validated with the same checker CI
uses, so a policy this tool writes cannot pass here and fail there.

It deliberately does not invent, default, or infer any of: the edition, the
approved base URL, the verifier, or the reviewer.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "n8n-policy.json"

sys.path.insert(0, str(ROOT / "scripts"))

from policy_common import meaningful_identity, valid_https_base  # noqa: E402
from policy_n8n import (  # noqa: E402
    ALLOWED_CREDENTIAL_STRATEGIES,
    ALLOWED_EDITOR_STRATEGIES,
    ALLOWED_ENDPOINT_STRATEGIES,
    validate_n8n_policy,
)


class AttestationError(RuntimeError):
    """Raised when the requested attestation is not supportable."""


def digest_artifact(label: str, path: Path) -> str:
    """Hash a real evidence artifact, refusing anything that proves nothing."""
    if not path.is_file():
        raise AttestationError(f"{label} evidence file does not exist: {path}")
    payload = path.read_bytes()
    if not payload.strip():
        raise AttestationError(f"{label} evidence file is empty: {path}")
    return hashlib.sha256(payload).hexdigest()


def build_policy(current: dict, args: argparse.Namespace) -> dict:
    if not meaningful_identity(args.verified_by):
        raise AttestationError("--verified-by must be a named person")
    if not meaningful_identity(args.independent_reviewer):
        raise AttestationError("--independent-reviewer must be a named person")
    if args.verified_by.strip().casefold() == args.independent_reviewer.strip().casefold():
        raise AttestationError(
            "the verifier and the independent reviewer must be different people"
        )
    if not meaningful_identity(args.edition) or args.edition.strip().casefold() == "unverified":
        raise AttestationError("--edition must name the n8n edition that was checked")
    if not valid_https_base(args.approved_base_url):
        raise AttestationError(
            "--approved-base-url must be a routable HTTPS origin; placeholder domains "
            "such as .invalid, .example, .test, localhost, and bare IPs are rejected"
        )

    verified_at = args.verified_at or dt.datetime.now(dt.timezone.utc).isoformat()

    policy = json.loads(json.dumps(current))
    policy.update(
        {
            "status": "VERIFIED",
            "edition": args.edition.strip(),
            "verified_at": verified_at,
            "verified_by": args.verified_by.strip(),
            "independent_reviewer": args.independent_reviewer.strip(),
            "evidence_sha256": digest_artifact("overall", args.evidence),
        }
    )
    policy["endpoint_binding"].update(
        {
            "status": "VERIFIED",
            "production_strategy": args.endpoint_strategy,
            "approved_base_url": args.approved_base_url,
            "egress_policy_evidence_sha256": digest_artifact("egress", args.egress_evidence),
        }
    )
    if args.endpoint_strategy == "verified-custom-variable":
        policy["endpoint_binding"]["custom_variables_supported"] = True
    policy["credential_binding"].update(
        {
            "status": "VERIFIED",
            "strategy": args.credential_strategy,
            "approved_types": list(dict.fromkeys(args.credential_type)),
            "approved_names": list(dict.fromkeys(args.credential_name)),
            "evidence_sha256": digest_artifact("credential", args.credential_evidence),
        }
    )
    policy["editor_access"].update(
        {
            "status": "VERIFIED",
            "strategy": args.editor_strategy,
            "publicly_routable": False,
            "evidence_sha256": digest_artifact("editor", args.editor_evidence),
            "session_policy_evidence_sha256": digest_artifact(
                "editor session policy", args.session_policy_evidence
            ),
        }
    )
    return policy


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", required=True)
    parser.add_argument("--verified-by", required=True)
    parser.add_argument("--independent-reviewer", required=True)
    parser.add_argument("--verified-at", default=None)
    parser.add_argument("--approved-base-url", required=True)
    parser.add_argument(
        "--endpoint-strategy",
        required=True,
        choices=sorted(ALLOWED_ENDPOINT_STRATEGIES),
    )
    parser.add_argument(
        "--credential-strategy",
        required=True,
        choices=sorted(ALLOWED_CREDENTIAL_STRATEGIES),
    )
    parser.add_argument("--credential-type", required=True, action="append")
    parser.add_argument("--credential-name", required=True, action="append")
    parser.add_argument(
        "--editor-strategy",
        required=True,
        choices=sorted(ALLOWED_EDITOR_STRATEGIES),
    )
    for name in (
        "--evidence",
        "--egress-evidence",
        "--credential-evidence",
        "--editor-evidence",
        "--session-policy-evidence",
    ):
        parser.add_argument(name, required=True, type=Path)
    parser.add_argument(
        "--write",
        action="store_true",
        help="write config/n8n-policy.json; without it the result is printed only",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    current = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    try:
        policy = build_policy(current, args)
    except AttestationError as exc:
        print(f"N8N_POLICY_ATTESTATION=REFUSED reason={exc}", file=sys.stderr)
        return 2

    errors, _ = validate_n8n_policy(policy)
    if errors:
        print("N8N_POLICY_ATTESTATION=REJECTED", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    rendered = json.dumps(policy, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        POLICY_PATH.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"N8N_POLICY_ATTESTATION=WRITTEN path={POLICY_PATH.relative_to(ROOT)}")
    else:
        print(rendered, end="")
        print("N8N_POLICY_ATTESTATION=VALID (dry run; pass --write to record it)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
