# Password validation — current policy

As of 2026-11-27, the user's cumulative-delivery request explicitly retires the external
compromised-password database requirement (DEC-27). The former Pwned Passwords range client,
SHA-1 comparison, timeout setting and `password_check_unavailable` error are removed.
Do not provision a corpus or external HTTPS access for password validation.

Registration, recovery, administrator creation and administrative password changes retain
Django's configured minimum 12 characters, attribute similarity, common-password and
numeric-password validators. Argon2id stores account passwords. No mandatory digit or
periodic expiry rule has been added. Login guards, CSRF, verification, single-use recovery
and session revocation remain unchanged.

The retained historical reports describe the earlier provider implementation; they are not
current setup instructions. Read [the consolidated report](consolidacion-iteraciones-01-03.md)
for current contracts and verification. `scripts/verify_hu007_http.py` now exercises local
weak-password rejection and does not query a password service; it is an optional manual
HTTP script and was not executed as part of this consolidation.
