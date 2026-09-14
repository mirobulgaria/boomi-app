from __future__ import annotations

import pytest

from boomi_builder.services.sensitive_value_redactor import (
    REDACTION_MARKER,
    SensitiveValueRedactor,
)


SYNTHETIC_SECRET = "SYNTHETIC_SECRET_NOT_REAL"
SYNTHETIC_TOKEN = "SYNTHETIC_TOKEN_NOT_REAL"
SYNTHETIC_PASSWORD = "SYNTHETIC_PASSWORD_NOT_REAL"


@pytest.fixture
def redactor() -> SensitiveValueRedactor:
    return SensitiveValueRedactor()


@pytest.mark.parametrize(
    "name",
    [
        "password",
        "PASSWORD",
        "passwd",
        "clientSecret",
        "ClientSecret",
        "client_secret",
        "client-secret",
        "CLIENT_SECRET",
        "apiToken",
        "api_token",
        "API_TOKEN",
        "accessToken",
        "access_token",
        "refreshToken",
        "refresh_token",
        "apiKey",
        "api_key",
        "authorization",
        "AUTHORIZATION",
        "privateKey",
        "private_key",
        "accessKey",
        "access_key",
        "secretKey",
        "secret_key",
        "token",
        "secret",
        "credential",
    ],
)
def test_sensitive_names_are_detected(
    redactor: SensitiveValueRedactor,
    name: str,
) -> None:
    assert redactor.is_sensitive_name(name) is True


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("password", SYNTHETIC_PASSWORD),
        ("clientSecret", SYNTHETIC_SECRET),
        ("client_secret", SYNTHETIC_SECRET),
        ("client-secret", SYNTHETIC_SECRET),
        ("CLIENT_SECRET", SYNTHETIC_SECRET),
        ("apiToken", SYNTHETIC_TOKEN),
        ("api_token", SYNTHETIC_TOKEN),
        ("accessToken", SYNTHETIC_TOKEN),
        ("refreshToken", SYNTHETIC_TOKEN),
        ("apiKey", SYNTHETIC_SECRET),
        ("authorization", SYNTHETIC_TOKEN),
        ("privateKey", SYNTHETIC_SECRET),
        ("accessKey", SYNTHETIC_SECRET),
        ("secretKey", SYNTHETIC_SECRET),
    ],
)
def test_sensitive_values_are_redacted(
    redactor: SensitiveValueRedactor,
    name: str,
    value: str,
) -> None:
    assert redactor.redact(name, value) == REDACTION_MARKER
    assert REDACTION_MARKER == "<REDACTED>"


@pytest.mark.parametrize(
    "name",
    [
        "allowDynamicCredentials",
        "credentialMode",
        "tokenize",
        "secretary",
        "passwordPolicy",
        "authorizationMode",
        "connectorType",
        "actionType",
        "mapId",
        "connectionId",
        "operationId",
        "userlabel",
    ],
)
def test_false_positive_names_are_not_sensitive(
    redactor: SensitiveValueRedactor,
    name: str,
) -> None:
    assert redactor.is_sensitive_name(name) is False


def test_false_positive_value_remains_unchanged(
    redactor: SensitiveValueRedactor,
) -> None:
    assert (
        redactor.redact(
            "allowDynamicCredentials",
            "false",
        )
        == "false"
    )


def test_non_sensitive_value_is_unchanged(
    redactor: SensitiveValueRedactor,
) -> None:
    value = "https-connector"
    assert (
        redactor.redact("connectorType", value)
        == value
    )


def test_empty_name_is_non_sensitive(
    redactor: SensitiveValueRedactor,
) -> None:
    assert redactor.is_sensitive_name("") is False
    assert (
        redactor.redact("", SYNTHETIC_SECRET)
        == SYNTHETIC_SECRET
    )


def test_whitespace_only_name_is_non_sensitive(
    redactor: SensitiveValueRedactor,
) -> None:
    assert redactor.is_sensitive_name("   ") is False
    assert (
        redactor.redact("   ", SYNTHETIC_SECRET)
        == SYNTHETIC_SECRET
    )


def test_non_sensitive_empty_value_remains_empty(
    redactor: SensitiveValueRedactor,
) -> None:
    assert redactor.redact("connectorType", "") == ""


def test_sensitive_empty_value_is_redacted(
    redactor: SensitiveValueRedactor,
) -> None:
    assert redactor.redact("password", "") == REDACTION_MARKER


def test_unicode_non_sensitive_name_unchanged(
    redactor: SensitiveValueRedactor,
) -> None:
    name = "описание"
    value = "пример"
    assert redactor.is_sensitive_name(name) is False
    assert redactor.redact(name, value) == value


def test_repeated_calls_are_deterministic(
    redactor: SensitiveValueRedactor,
) -> None:
    first = redactor.redact(
        "clientSecret",
        SYNTHETIC_SECRET,
    )
    second = redactor.redact(
        "clientSecret",
        SYNTHETIC_SECRET,
    )
    assert first == second == REDACTION_MARKER

    safe_first = redactor.redact(
        "credentialMode",
        "managed",
    )
    safe_second = redactor.redact(
        "credentialMode",
        "managed",
    )
    assert safe_first == safe_second == "managed"


def test_business_field_names_are_not_sensitive_by_default(
    redactor: SensitiveValueRedactor,
) -> None:
    assert redactor.is_sensitive_name("orderId") is False
    assert (
        redactor.is_sensitive_name("partnerEndpoint")
        is False
    )
    assert (
        redactor.redact("orderId", "ORD-1") == "ORD-1"
    )
