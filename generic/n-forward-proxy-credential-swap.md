---
layout: document
kind: generic
id: n-forward-proxy-credential-swap
title: Forward Proxy Credential Swap Trust Requirements
created: 2026-03-25
parameter: "forward proxy intercepting TLS that replaces sentinel tokens with real credentials"
evidence:
  - type: citation
    ref: "NIST SP 800-204A: Building Secure Microservices-based Applications Using Service-Mesh Architecture"
  - type: citation
    ref: "Saltzer, Schroeder. The Protection of Information in Computer Systems. Proceedings of the IEEE, 1975."
---

# Forward Proxy Credential Swap Trust Requirements

For any forward proxy that intercepts TLS connections and swaps sentinel tokens for real credentials, the following trust boundary properties must hold.

## Required Properties

1. **Isolation of credential store:** The real credentials must not be accessible to the process whose traffic is being proxied. The proxy holds credentials; the client holds only sentinels.

2. **TLS termination scope:** The proxy must terminate the client's outbound TLS, inspect/modify the request, then establish a new TLS connection to the upstream. The client trusts the proxy's CA.

3. **Sentinel uniqueness:** Sentinel tokens must be non-guessable and per-session or per-request to prevent replay by a compromised client.

4. **Audit completeness:** Every credential swap must be logged with the sentinel used, the upstream destination, and the timestamp. The log is append-only and not writable by the proxied process.

5. **Blast radius containment:** A compromised proxy reveals credentials only for the upstreams it is configured to reach. No proxy should hold credentials for all upstreams.

## Anti-Patterns

- Sharing the proxy's credential store with the client process (defeats isolation)
- Using long-lived sentinel tokens (enables replay attacks)
- Running the proxy as the same user/namespace as the client (no privilege boundary)
