#!/usr/bin/env python3
"""Classify a Paper Trail worker endpoint without performing network I/O."""

import ipaddress
from urllib.parse import urlparse


def _result(
    classification,
    *,
    trusted=False,
    requires_desensitized=False,
    transport_allowed=False,
):
    return {
        "classification": classification,
        "trusted": trusted,
        "requires_desensitized": requires_desensitized,
        "transport_allowed": transport_allowed,
    }


def _normalize_trusted_hosts(trusted_hosts):
    if isinstance(trusted_hosts, str):
        trusted_hosts = trusted_hosts.split(",")
    return {
        str(item).strip().casefold().rstrip(".")
        for item in (trusted_hosts or ())
        if str(item).strip()
    }


def classify_worker_endpoint(base_url, trusted_hosts=()):
    """Return the worker data-boundary classification and transport policy."""
    if base_url is None or not str(base_url).strip():
        return _result("unconfigured")
    if not isinstance(base_url, str) or base_url != base_url.strip():
        return _result("invalid")

    try:
        parsed = urlparse(base_url)
        host = parsed.hostname
        # Accessing port validates malformed port declarations.
        parsed.port
    except ValueError:
        return _result("invalid")

    if (
        parsed.scheme not in {"http", "https"}
        or not host
        or parsed.username
        or parsed.password
    ):
        return _result("invalid")

    host = host.casefold().rstrip(".")
    configured_hosts = _normalize_trusted_hosts(trusted_hosts)
    trusted = (
        host in configured_hosts
        or host == "localhost"
        or host.endswith((".localhost", ".local", ".internal"))
    )
    if not trusted:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            trusted = (
                address.is_private
                or address.is_loopback
                or address.is_link_local
            )

    if trusted:
        return _result(
            "trusted-local",
            trusted=True,
            transport_allowed=True,
        )
    if parsed.scheme == "https":
        return _result(
            "external-https",
            requires_desensitized=True,
            transport_allowed=True,
        )
    return _result(
        "external-http-blocked",
        requires_desensitized=True,
    )
