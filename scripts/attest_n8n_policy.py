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
RUNTIME_PATH = ROOT / "config" / "n8n-community-runtime.v1.json"
EGRESS_PATH = ROOT / "deploy" / "egress" / "n8n-egress-policy.v1.json"

sys.path.insert(0, str(ROOT / "scripts"))

from policy_common import (  # noqa: E402
    meaningful_identity,
    valid_https_base,
    valid_iso8601,
)
from policy_n8n import (  # noqa: E402
    ALLOWED_CREDENTIAL_STRATEGIES,
    ALLOWED_EDITOR_STRATEGIES,
    ALLOWED_ENDPOINT_STRATEGIES,
    validate_n8n_policy,
)
from policy_community_runtime import validate_community_runtime_policy  # noqa: E402


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


def require_distinct_evidence(args: argparse.Namespace) -> None:
    """Refuse an attestation whose bindings all point at the same artifact.

    The policy carries a separate hash per binding so each one is separately
    evidenced. Passing a single bundle five times produces five identical hashes
    and proves nothing about four of the five bindings.
    """
    seen: dict[str, str] = {}
    collisions: list[str] = []
    for label, path in (
        ("--evidence", args.evidence),
        ("--egress-evidence", args.egress_evidence),
        ("--credential-evidence", args.credential_evidence),
        ("--editor-evidence", args.editor_evidence),
        ("--session-policy-evidence", args.session_policy_evidence),
    ):
        digest = digest_artifact(label, path)
        if digest in seen:
            collisions.append(f"{label} duplicates {seen[digest]}")
        else:
            seen[digest] = label
    if collisions:
        raise AttestationError(
            "each binding needs its own evidence; " + "; ".join(collisions)
        )


def build_policy(
    current: dict, args: argparse.Namespace, runtime: dict | None = None
) -> dict:
    runtime = runtime or json.loads(RUNTIME_PATH.read_text(encoding="utf-8"))
    runtime_image = runtime.get("runtime_image", {})
    runtime_credential = runtime.get("credential", {})
    runtime_endpoint = runtime.get("endpoint", {})
    approved_version = runtime_image.get("approved_image_version")
    if runtime_image.get("status") != "VERIFIED" or not isinstance(approved_version, str):
        raise AttestationError(
            "runtime image evidence must be VERIFIED before binding attestation"
        )
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
    expected_edition = f"n8n Community Edition {approved_version}"
    if args.edition.strip() != expected_edition:
        raise AttestationError(
            f"--edition must match the verified runtime image: {expected_edition}"
        )
    if not valid_https_base(args.approved_base_url):
        raise AttestationError(
            "--approved-base-url must be a routable HTTPS origin; placeholder domains "
            "such as .invalid, .example, .test, localhost, and bare IPs are rejected"
        )

    if args.verified_at is not None and not valid_iso8601(args.verified_at):
        raise AttestationError("--verified-at must be a timezone-aware ISO 8601 timestamp")
    now = dt.datetime.now(dt.timezone.utc)
    verified_at = args.verified_at or now.isoformat()
    parsed_verified_at = dt.datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
    if parsed_verified_at > now + dt.timedelta(minutes=5):
        raise AttestationError("--verified-at must not be in the future")

    require_distinct_evidence(args)
    if len(args.credential_type) != 1 or len(args.credential_name) != 1:
        raise AttestationError(
            "exactly one credential type/name pair may be attested per policy"
        )
    if args.approved_base_url != runtime_endpoint.get("base_url"):
        raise AttestationError("endpoint must match the canonical community runtime")
    if args.endpoint_strategy != "verified-fixed-private-dns":
        raise AttestationError("community runtime requires the fixed private-DNS strategy")
    if args.credential_type != [runtime_credential.get("type")] or args.credential_name != [
        runtime_credential.get("name")
    ]:
        raise AttestationError("credential type and name must match the canonical runtime")
    if args.credential_strategy != "verified-n8n-credential":
        raise AttestationError("community runtime requires an n8n-owned credential")
    if args.editor_strategy != "verified-gateway-oidc-and-native-auth":
        raise AttestationError("editor strategy must match the canonical runtime")

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
    policy["endpoint_binding"]["custom_variables_supported"] = (
        args.endpoint_strategy == "verified-custom-variable"
    )
    policy["credential_binding"].update(
        {
            "status": "VERIFIED",
            "strategy": args.credential_strategy,
            "approved_types": list(dict.fromkeys(args.credential_type)),
            "approved_names": list(dict.fromkeys(args.credential_name)),
            "approved_ids": [args.credential_id],
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
    parser.add_argument("--credential-id", required=True)
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
    runtime = json.loads(RUNTIME_PATH.read_text(encoding="utf-8"))
    egress = json.loads(EGRESS_PATH.read_text(encoding="utf-8"))
    try:
        policy = build_policy(current, args, runtime)
    except AttestationError as exc:
        print(f"N8N_POLICY_ATTESTATION=REFUSED reason={exc}", file=sys.stderr)
        return 2

    errors, _ = validate_n8n_policy(policy)
    errors.extend(validate_community_runtime_policy(policy, runtime, egress))
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
