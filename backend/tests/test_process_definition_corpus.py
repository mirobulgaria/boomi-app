from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from boomi_builder.settings import get_app_paths


def _run_fingerprint_harness(
    *,
    xml: str,
) -> subprocess.CompletedProcess[str]:
    paths = get_app_paths()
    read_file = paths.engine_root / "lib" / "Boomi.Read.ps1"

    script = f"""
$ErrorActionPreference = "Stop"

. "{read_file}"

$xmlText = @'
{xml}
'@

[xml]$configNode = $xmlText

$fingerprint = Get-ProcessShapeStructuralFingerprint `
    -ConfigurationNode $configNode

Write-Host "FINGERPRINT: $fingerprint"

exit 0
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = Path(temp_dir) / "fingerprint_harness.ps1"
        script_path.write_text(
            script,
            encoding="utf-8",
        )

        return subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )


def test_fingerprint_ignores_attribute_values() -> None:
    xml = """
<configuration>
    <connectoraction
        actionType="EXECUTE"
        password="SECRET_PASSWORD"
        apiToken="SECRET_TOKEN"
        connectionId="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa">
    </connectoraction>
</configuration>
"""

    result = _run_fingerprint_harness(xml=xml)

    assert result.returncode == 0

    output = result.stdout

    assert "FINGERPRINT:" in output

    # Attribute values should NOT appear in fingerprint
    assert "SECRET_PASSWORD" not in output
    assert "SECRET_TOKEN" not in output
    assert "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa" not in output

    # Attribute names SHOULD appear
    assert "actionType" in output
    assert "password" in output
    assert "apiToken" in output
    assert "connectionId" in output


def test_fingerprint_ignores_element_text() -> None:
    xml = """
<configuration>
    <message>
        <msgTxt>SENSITIVE_MESSAGE_CONTENT</msgTxt>
    </message>
</configuration>
"""

    result = _run_fingerprint_harness(xml=xml)

    assert result.returncode == 0

    output = result.stdout

    assert "FINGERPRINT:" in output

    # Element text should NOT appear
    assert "SENSITIVE_MESSAGE_CONTENT" not in output

    # Element names SHOULD appear
    assert "message" in output
    assert "msgTxt" in output


def test_fingerprint_includes_attribute_names() -> None:
    xml1 = """
<configuration>
    <shape attr1="value1" attr2="value2"/>
</configuration>
"""

    xml2 = """
<configuration>
    <shape attr1="different" attr2="different"/>
</configuration>
"""

    result1 = _run_fingerprint_harness(xml=xml1)
    result2 = _run_fingerprint_harness(xml=xml2)

    assert result1.returncode == 0
    assert result2.returncode == 0

    # Fingerprints should be identical (only attribute names matter)
    fingerprint1 = result1.stdout.split("FINGERPRINT: ")[1].strip()
    fingerprint2 = result2.stdout.split("FINGERPRINT: ")[1].strip()

    assert fingerprint1 == fingerprint2


def test_fingerprint_includes_nested_structure() -> None:
    xml1 = """
<configuration>
    <parent>
        <child>text</child>
    </parent>
</configuration>
"""

    xml2 = """
<configuration>
    <parent>
        <child>different</child>
    </parent>
</configuration>
"""

    xml3 = """
<configuration>
    <parent>
        <otherchild>text</otherchild>
    </parent>
</configuration>
"""

    result1 = _run_fingerprint_harness(xml=xml1)
    result2 = _run_fingerprint_harness(xml=xml2)
    result3 = _run_fingerprint_harness(xml=xml3)

    assert result1.returncode == 0
    assert result2.returncode == 0
    assert result3.returncode == 0

    fingerprint1 = result1.stdout.split("FINGERPRINT: ")[1].strip()
    fingerprint2 = result2.stdout.split("FINGERPRINT: ")[1].strip()
    fingerprint3 = result3.stdout.split("FINGERPRINT: ")[1].strip()

    # xml1 and xml2 should be identical (element name matters, not text)
    assert fingerprint1 == fingerprint2

    # xml3 should differ (different child element name)
    assert fingerprint1 != fingerprint3


def test_fingerprint_cardinality_affects_result() -> None:
    xml1 = """
<configuration>
    <shape/>
</configuration>
"""

    xml2 = """
<configuration>
    <shape/>
    <shape/>
</configuration>
"""

    result1 = _run_fingerprint_harness(xml=xml1)
    result2 = _run_fingerprint_harness(xml=xml2)

    assert result1.returncode == 0
    assert result2.returncode == 0

    fingerprint1 = result1.stdout.split("FINGERPRINT: ")[1].strip()
    fingerprint2 = result2.stdout.split("FINGERPRINT: ")[1].strip()

    # Different cardinality should produce different fingerprints
    assert fingerprint1 != fingerprint2


def test_fingerprint_unknown_elements_represented_generically() -> None:
    xml = """
<configuration>
    <unknown_element customAttr="value">
        <nested_unknown>nested text</nested_unknown>
    </unknown_element>
</configuration>
"""

    result = _run_fingerprint_harness(xml=xml)

    assert result.returncode == 0

    output = result.stdout

    assert "FINGERPRINT:" in output

    # Element names should be present (generic representation)
    assert "unknown_element" in output
    assert "nested_unknown" in output
    assert "customAttr" in output

    # Values should NOT be present
    assert "value" not in output
    assert "nested text" not in output


def test_corpus_command_requires_app_readonly_mode() -> None:
    # This test is now covered by test_app_readonly_allowlist_is_exact
    # and the parameterized blocked command tests in test_app_readonly_safety.py
    pass
