#!/bin/sh
set -eu

# These are enforcement inputs, not informational labels. The staging runtime
# must refuse to start unless every umbrella is explicitly and exactly closed.
for control in \
    LIVE_ADVERTISING_ENABLED \
    EXTERNAL_DELIVERY_ENABLED \
    SOCIAL_PUBLISHING_ENABLED \
    EXTERNAL_MODEL_CALLS_ENABLED \
    N8N_EXTERNAL_PROVIDER_WRITES
do
    if [ "$(printenv "$control" 2>/dev/null || true)" != "false" ]; then
        echo "N8N_UMBRELLA_GUARD=FAIL control=$control" >&2
        exit 78
    fi
done

# Closed umbrellas rely on the reviewed Middleware-only route and deny-by-
# default egress layers. Refuse startup if either application egress invariant
# drifts; direct provider endpoints must remain unreachable.
if [ "${N8N_SSRF_PROTECTION_ENABLED:-}" != "true" ] || \
   [ "${N8N_SSRF_ALLOWED_HOSTNAMES:-}" != "api.codestra.co,auth.codestra.co" ] || \
   [ "${N8N_SSRF_BLOCKED_IP_RANGES:-}" != "0.0.0.0/0,::/0" ]; then
    echo "N8N_UMBRELLA_GUARD=FAIL egress=not_fail_closed" >&2
    exit 78
fi

echo "N8N_UMBRELLA_GUARD=PASS"
exec /docker-entrypoint.sh "$@"
