# Contributing

**Copyright © 2026 Olivier RENAULT — Apache-2.0**


Contributions are welcome.

Before opening a pull request:

1. keep changes focused on the generic RFPY use case;
2. add or update tests for behavior changes;
3. run `python tools/embed_payloads.py` after editing embedded runtime files;
4. run `python -m unittest discover -s tests -v`;
5. do not commit credentials, private repository URLs, internal certificates or organization-specific configuration.

The public implementation should remain vendor-neutral and reusable by the Robot Framework community.
