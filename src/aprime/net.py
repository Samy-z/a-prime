"""Network setup.

On machines behind a TLS-inspecting proxy, Python's bundled CA bundle does not
contain the interception certificate, so every HTTPS call fails with
CERTIFICATE_VERIFY_FAILED even though the browser on the same machine is fine.
`truststore` makes Python read the operating system's certificate store, which
does contain it.

The alternative fixes are both wrong for this repo. Disabling verification
would silently accept any certificate, and the study's own provenance rail
depends on knowing that the weights we downloaded came from the host we think
they did. Hardcoding a corporate root would not travel to anyone else's
machine.

Call `enable_os_truststore()` before importing anything that opens a
connection: the patch works by installing an SSL context factory, and a client
that has already built its context will not pick it up.
"""

from __future__ import annotations

import warnings


def enable_os_truststore() -> bool:
    """Route Python TLS verification through the OS certificate store.

    Returns True if the patch was applied. A False return is not fatal — on a
    machine without TLS interception the default bundle works fine — so the
    caller should carry on rather than abort.
    """
    try:
        import truststore
    except ImportError:
        warnings.warn(
            "truststore not installed; HTTPS will use Python's bundled CA "
            "bundle and may fail behind a TLS-inspecting proxy "
            "(pip install truststore)",
            stacklevel=2,
        )
        return False
    truststore.inject_into_ssl()
    return True
