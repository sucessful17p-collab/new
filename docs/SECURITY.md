# Security and data retention

The service is intended for a trusted local network. It currently has no user authentication, role-based authorization, or rate limiting; do not expose it publicly without adding those controls. Configure allowed browser origins through `CORS_ORIGINS`, and keep provider credentials in environment secrets rather than source control.

Upload names are reduced to basenames, extensions are allow-listed, contents are size-capped, and uploaded bytes are never executed. File contents are treated as data. Markdown output is exported as plain text; the UI renders extracted content as React text, not raw HTML. SQL access uses SQLAlchemy parameterized operations.

Data remains in the configured database and upload directory until a user deletes the project or the operator removes the persistent volume. Back up or remove both together. Source documents are never changed. No claim is made of end-to-end encryption, zero telemetry, or local-only model inference.
