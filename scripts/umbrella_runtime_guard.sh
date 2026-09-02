#!/bin/sh
set -eu

# The sentinel keeps printenv's final newline inside command substitution, so
# values such as "false<newline>" cannot be normalized to the accepted value.
expected_false="$(printf 'false\n__CODESTRA_VALUE_END__')"
for control in \
    LIVE_ADVERTISING_ENABLED \
    EXTERNAL_DELIVERY_ENABLED \
    SOCIAL_PUBLISHING_ENABLED \
    EXTERNAL_MODEL_CALLS_ENABLED \
    N8N_EXTERNAL_PROVIDER_WRITES
do
    actual="$({ printenv "$control" 2>/dev/null || true; printf '__CODESTRA_VALUE_END__'; })"
    if [ "$actual" != "$expected_false" ]; then
        echo "N8N_UMBRELLA_GUARD=FAIL control=$control" >&2
        exit 78
    fi
done

if [ "${N8N_SSRF_PROTECTION_ENABLED:-}" != "true" ] || \
   [ "${N8N_SSRF_ALLOWED_HOSTNAMES:-}" != "api.codestra.co,auth.codestra.co" ] || \
   [ "${N8N_SSRF_BLOCKED_IP_RANGES:-}" != "0.0.0.0/0,::/0" ]; then
    echo "N8N_UMBRELLA_GUARD=FAIL egress=not_fail_closed" >&2
    exit 78
fi

echo "N8N_UMBRELLA_GUARD=PASS"
exec /docker-entrypoint.sh "$@"
