import os
import sys
import pytest
import binascii
import pickle
import json

# Add src to path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import credentials_manager as CredentialsManager
import flash_verify
import sungur_client
import dpapi_win


def test_password_generation_standard():
    """Verifies that generated password adheres to original 8-character alphanumeric standard."""
    p = CredentialsManager.generate_random_password()
    assert len(p) == 8
    assert p.isalnum()


def test_safe_unpickler_allowlist(tmp_path):
    """Verifies SafeUnpickler allows valid hexlified data and blocks arbitrary unsafe objects."""
    # 1. Valid data
    valid_payload = json.dumps({"username": "test_teacher", "serial": "223C-F3F8"}).encode("utf-8")
    hexlified = binascii.hexlify(valid_payload)
    test_cred = tmp_path / ".credentials"
    with open(test_cred, "wb") as f:
        pickle.dump(hexlified, f)

    with open(test_cred, "rb") as f:
        unpickler = flash_verify.SafeUnpickler(f)
        obj = unpickler.load()
    assert obj == hexlified

    # 2. Malicious payload attempt
    class Exploit:
        def __reduce__(self):
            return (os.system, ("echo hacked",))

    bad_cred = tmp_path / "bad.credentials"
    with open(bad_cred, "wb") as f:
        pickle.dump(Exploit(), f)

    with open(bad_cred, "rb") as f:
        unpickler = flash_verify.SafeUnpickler(f)
        with pytest.raises(pickle.UnpicklingError):
            unpickler.load()


def test_flash_verify_offline_mode(tmp_path):
    """Verifies that offline EBA check yields skipped status instead of breaking validation."""
    test_cred = tmp_path / ".credentials"
    raw_json = {
        "name": "Ahmet Yilmaz",
        "username": "ahmet.yilmaz",
        "tckn": "11111111110",
        "eba_id": "12345678",
        "usb_serial": "223C-F3F8",
        "password": "$2b$12$e8YkC2L9xUv7F3K9K3H7DeJvB7J3M3P1N9T5R7W9Q1S3U5V7X9Z1."
    }
    hexlified = binascii.hexlify(json.dumps(raw_json).encode("utf-8"))
    with open(test_cred, "wb") as f:
        pickle.dump(hexlified, f)

    dev = {
        "mountpoint": str(tmp_path),
        "serial": "223C-F3F8",
        "label": "FATIH_USB"
    }

    # check_server=True with mock session returning None (offline)
    class MockOfflineSession:
        def get(self, *args, **kwargs):
            raise Exception("No network connection")

    res = flash_verify.verify_flash(dev, check_server=True, session=MockOfflineSession())
    assert res["ok"] is True
    eba_check = next((c for c in res["checks"] if c[0] == "EBA kaydı"), None)
    assert eba_check is not None
    assert eba_check[1] == "skipped"


def test_sungur_url_normalization():
    """Verifies that sungur_client normalizes HTTP/HTTPS endpoints with secure defaults."""
    assert sungur_client.normalize_sungur_url("etap-sungur.local:8443") == "https://etap-sungur.local:8443"
    assert sungur_client.normalize_sungur_url("http://192.168.0.67:8080") == "http://192.168.0.67:8080"
    assert sungur_client.normalize_sungur_url("192.168.0.67") == "https://192.168.0.67"


def test_dpapi_secret_protection_roundtrip():
    """Verifies encryption and decryption roundtrip for admin token."""
    plain = "sungur_secret_token_12345"
    protected = dpapi_win.protect_secret(plain)
    assert protected != plain
    unprotected = dpapi_win.unprotect_secret(protected)
    assert unprotected == plain


def test_qsettings_ini_format(tmp_path):
    """Verifies QSettings IniFormat reads/writes to a file with sync."""
    from PySide6.QtCore import QSettings
    ini_file = str(tmp_path / "sungur.ini")
    settings = QSettings(ini_file, QSettings.IniFormat)
    settings.setValue("sungur_url", "https://192.168.0.67:8443")
    token_prot = dpapi_win.protect_secret("my_admin_token")
    settings.setValue("sungur_token", token_prot)
    settings.sync()

    # Re-open and verify
    settings2 = QSettings(ini_file, QSettings.IniFormat)
    assert settings2.value("sungur_url") == "https://192.168.0.67:8443"
    assert dpapi_win.unprotect_secret(settings2.value("sungur_token")) == "my_admin_token"


def test_discovery_candidate_ips():
    """Verifies candidate IP generation contains defaults and hint URL host."""
    cands = sungur_client.get_discovery_candidate_ips(hint_url="https://192.168.2.88:8443")
    assert "192.168.2.88" in cands
    assert "192.168.0.67" in cands
    assert "etap-sungur.local" in cands


def test_discovery_udp_probe(monkeypatch):
    """Verifies that UDP discovery correctly parses server beacon / probe response."""
    mock_response = json.dumps({
        "service": "etap-sungur-server",
        "server_ip": "192.168.1.150",
        "server_port": 8080,
        "name": "ETAP Sungur Test"
    }).encode("utf-8")

    class MockSocket:
        def __init__(self, *args, **kwargs):
            pass
        def setsockopt(self, *args, **kwargs):
            pass
        def settimeout(self, *args, **kwargs):
            pass
        def sendto(self, data, addr):
            pass
        def recvfrom(self, bufsize):
            return mock_response, ("192.168.1.150", 7889)
        def close(self):
            pass

    monkeypatch.setattr("socket.socket", MockSocket)
    # Monkeypatch verify endpoint to succeed
    monkeypatch.setattr(sungur_client, "_verify_http_endpoint", lambda ip, port, is_https, timeout=0.8: True)

    res = sungur_client._probe_udp_discovery(timeout=0.5)
    assert res is not None
    assert res["ip"] == "192.168.1.150"
    assert res["port"] == 8080
    assert res["url"] == "http://192.168.1.150:8080"
    assert res["service"] == "etap-sungur-server"


def test_discovery_tcp_port_probe_fallback(monkeypatch):
    """Verifies multi-port fallback when UDP fails or is blocked."""
    # Force UDP to fail
    monkeypatch.setattr(sungur_client, "_probe_udp_discovery", lambda *args, **kwargs: None)

    # Allow mock verify to succeed only for specific target
    def mock_verify(ip, port, is_https, timeout=0.6):
        return ip == "192.168.0.67" and port == 8443

    monkeypatch.setattr(sungur_client, "_verify_http_endpoint", mock_verify)

    res = sungur_client.discover_sungur_server(timeout=1.0)
    assert res is not None
    assert res["ip"] == "192.168.0.67"
    assert res["port"] == 8443
    assert res["url"] == "https://192.168.0.67:8443"
    assert res["source"] == "tcp_port_probe"


def test_load_candidate_ips_from_config(tmp_path):
    """Verifies reading candidate_ips and sungur_url from custom sungur.ini."""
    ini_file = tmp_path / "sungur.ini"
    ini_file.write_text(
        "[General]\n"
        "sungur_url = https://192.168.3.45:8443\n"
        "candidate_ips = 192.168.5.10, 192.168.5.20; 10.10.10.50\n",
        encoding="utf-8"
    )

    loaded = sungur_client.load_candidate_ips_from_config(str(ini_file))
    assert "192.168.5.10" in loaded
    assert "192.168.5.20" in loaded
    assert "10.10.10.50" in loaded
    assert "192.168.3.45" in loaded

    # Verify discovery candidate list prioritizes config candidates
    cands = sungur_client.get_discovery_candidate_ips(config_path=str(ini_file))
    assert cands[0] == "192.168.5.10"
    assert "192.168.0.67" in cands  # Standard defaults still present as fallback


def test_dpapi_empty_handling():
    """Verifies that protect_secret with empty or None input returns empty string, not None."""
    assert dpapi_win.protect_secret("") == ""
    assert dpapi_win.protect_secret(None) == ""


def test_dpapi_error_handling_mock(monkeypatch):
    """Verifies that protect_secret returns None on exception to prevent overwriting saved token."""
    import sys
    monkeypatch.setattr(sys, "platform", "win32")
    # Simulate a failure in CryptProtectData
    import types
    fake_ctypes = types.ModuleType("ctypes")
    class FakeWindll:
        class crypt32:
            @staticmethod
            def CryptProtectData(*args, **kwargs):
                return 0  # Failure
    fake_ctypes.windll = FakeWindll()
    fake_ctypes.wintypes = types.ModuleType("wintypes")
    fake_ctypes.wintypes.DWORD = int
    fake_ctypes.c_byte = int
    fake_ctypes.Structure = object
    fake_ctypes.POINTER = lambda x: x
    fake_ctypes.cast = lambda a, b: a
    fake_ctypes.create_string_buffer = lambda x: x
    fake_ctypes.byref = lambda x: x

    monkeypatch.setitem(sys.modules, "ctypes", fake_ctypes)
    monkeypatch.setitem(sys.modules, "ctypes.wintypes", fake_ctypes.wintypes)

    result = dpapi_win.protect_secret("test_token")
    assert result is None
