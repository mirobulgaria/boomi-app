from __future__ import annotations

from re import sub


REDACTION_MARKER = "<REDACTED>"

# Canonical forms are lowercase semantic words joined with no separators.
# Matching is exact on the full canonical name — never substring/token-in-name.
_SENSITIVE_CANONICAL_NAMES = frozenset(
    {
        "password",
        "passwd",
        "token",
        "apitoken",
        "accesstoken",
        "refreshtoken",
        "apikey",
        "clientsecret",
        "secret",
        "credential",
        "authorization",
        "accesskey",
        "secretkey",
        "privatekey",
    }
)


class SensitiveValueRedactor:
    """Name-based redaction for safe presentation boundaries.

    Sensitivity is decided only from the field/attribute name.
    Value content is never inspected.
    """

    def is_sensitive_name(self, name: str) -> bool:
        canonical = self._canonical_name(name)
        if not canonical:
            return False
        return canonical in _SENSITIVE_CANONICAL_NAMES

    def redact(self, name: str, value: str) -> str:
        if self.is_sensitive_name(name):
            return REDACTION_MARKER
        return value

    @staticmethod
    def _canonical_name(name: str) -> str:
        stripped = name.strip()
        if not stripped:
            return ""

        # Treat common separators as word boundaries.
        spaced = sub(r"[\s_-]+", " ", stripped)

        # Split camelCase / PascalCase into semantic words.
        spaced = sub(
            r"(?<=[a-z0-9])(?=[A-Z])",
            " ",
            spaced,
        )
        spaced = sub(
            r"(?<=[A-Z])(?=[A-Z][a-z])",
            " ",
            spaced,
        )

        words = [
            word.lower()
            for word in spaced.split()
            if word
        ]
        return "".join(words)
