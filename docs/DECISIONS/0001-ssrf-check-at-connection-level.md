# 0001 — Enforce the SSRF check at connection level
Date: 2026-11-07 · Status: accepted

## Context
`/proxy` fetches any URL a client passes in. Once the server is reachable by
others, that lets them make it call loopback, the LAN or cloud metadata
endpoints. `app.run` binds to localhost today, so the exposure is not live yet.
The project has few dependencies and pins all of them.

## Problem
Where should the "public addresses only" rule be enforced so that it also holds
for redirects and for host names whose DNS answer changes between check and
connect?

## Options
**A: Pre-flight check of the URL, then a normal `requests.get`**
- Pro: about 15 lines, no library internals.
- Con: DNS is resolved twice, so a rebinding host passes the check and then
  connects internally. Redirects need a hand-written follow loop.

**B: Check inside the connection (custom urllib3 connection classes behind a
`requests` `HTTPAdapter`)**
- Pro: the checked address is the connected address, so there is no rebinding
  window. Every redirect hop is covered without extra code. Host header, SNI and
  certificate verification keep using the host name. No new dependency.
- Con: overrides `_new_conn`, a private urllib3 method. An urllib3 upgrade that
  renames it would silently remove the guard.

**C: Third-party SSRF library (e.g. `advocate`)**
- Pro: logic maintained elsewhere.
- Con: new dependency in a security path; its compatibility with current
  `requests`/`urllib3` and its maintenance status were not evaluated.

## Recommendation
B. It is the only option here that closes both redirects and DNS rebinding
without a new dependency. The private-method risk is covered by tests that run
against a real loopback server: if the override stops taking effect,
`test_loopback_is_never_contacted` fails.

## Decision
Option B, in the user's words: "Ja, Option B".

## Consequences
- Rerun the SSRF tests on every urllib3 or requests upgrade.
- Only the first resolved address is tried (IPv4 preferred), so there is no
  fallback to further addresses of a host.
- Environment proxies are ignored (`trust_env = False`). An outbound proxy
  requirement would mean revisiting this decision.
- Images cached before this change are still served without a check.
