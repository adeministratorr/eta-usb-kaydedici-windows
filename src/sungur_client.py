import socket
import json
import urllib.parse
import requests
import urllib3
from typing import Dict, Any, Tuple, Optional, List

# Disable InsecureRequestWarning for local self-signed certificates on school fleet server
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_SUNGUR_URL = "https://etap-sungur.local:8443"
FALLBACK_SUNGUR_URL = "http://etap-sungur.local:8080"
REQUEST_TIMEOUT = 45

DISCOVERY_UDP_PORT = 7889
DISCOVERY_PROBE_PAYLOAD = b"ETAP_DISCOVER_PROBE"
import os
import configparser

# FATIH Project Network Topology:
# - Interactive Board Network (VLAN 1): 10.x.y.z (can route to administrative network)
# - Administrative Network (VLAN 2): 192.168.0.0/21 (192.168.0.x - 192.168.7.x, where Sungur Server resides)
# - IT / Lab Network (VLAN 3): 192.168.16.0/21 (192.168.16.x - 192.168.23.x, isolated)
DEFAULT_CANDIDATE_IPS = [
    "192.168.0.67",    # Primary Sungur Server IP in Administrative Network
    "192.168.1.50",    # Secondary Administrative Server IP
    "192.168.0.50",
    "192.168.1.100",
    "192.168.0.100",
    "etap-sungur.local",
    "10.0.0.50",       # Interactive board subnet fallback
    "127.0.0.1"
]
KNOWN_CANDIDATE_IPS = list(DEFAULT_CANDIDATE_IPS)
KNOWN_PROBE_PORTS = [8443, 8080, 443, 80]

def get_config_path() -> Optional[str]:
    """Resolves standard config file location across Windows and Linux."""
    # 1. Windows AppData
    appdata = os.environ.get("APPDATA")
    if appdata:
        win_path = os.path.join(appdata, "SelcukluMTAL", "EtaUsbKaydedici", "sungur.ini")
        if os.path.exists(win_path):
            return win_path

    # 2. Linux system config
    for linux_path in ["/etc/etap-sungur-server.conf", "/etc/etap-fleet-server.conf"]:
        if os.path.exists(linux_path):
            return linux_path

    # 3. Local directory fallback
    local_ini = os.path.join(os.path.dirname(__file__), "..", "sungur.ini")
    if os.path.exists(local_ini):
        return local_ini

    return None

def load_candidate_ips_from_config(config_path: Optional[str] = None) -> List[str]:
    """
    Loads custom candidate IPs from sungur.ini or /etc/etap-sungur-server.conf.
    Reads 'candidate_ips' and 'sungur_url' options from INI or plain IP list.
    """
    path = config_path or get_config_path()
    if not path or not os.path.exists(path):
        return []

    found_ips: List[str] = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().strip()

        if not content:
            return []

        # Check if INI format (has sections or key=value)
        if "[" in content or "=" in content:
            cp = configparser.ConfigParser()
            # If no section header, prepend dummy section
            ini_text = content if "[" in content else f"[General]\n{content}"
            cp.read_string(ini_text)
            for sec in cp.sections():
                # 1. Custom candidate_ips option
                if cp.has_option(sec, "candidate_ips"):
                    raw = cp.get(sec, "candidate_ips")
                    for item in raw.replace(";", ",").split(","):
                        ip = item.strip()
                        if ip and ip not in found_ips:
                            found_ips.append(ip)

                # 2. Extract host from configured sungur_url
                if cp.has_option(sec, "sungur_url"):
                    raw_url = cp.get(sec, "sungur_url").strip()
                    try:
                        parsed = urllib.parse.urlparse(normalize_sungur_url(raw_url))
                        if parsed.hostname and parsed.hostname not in found_ips:
                            found_ips.append(parsed.hostname)
                    except Exception:
                        pass
        else:
            # Plain text config (e.g. /etc/etap-sungur-server.conf with IP:PORT or plain IPs)
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    ip = line.split(":", 1)[0].strip()
                    if ip and ip not in found_ips:
                        found_ips.append(ip)
    except Exception:
        pass

    return found_ips

def normalize_sungur_url(url: Optional[str]) -> str:
    """Normalizes Sungur base URL, adding https:// if protocol is omitted."""
    raw = (url or DEFAULT_SUNGUR_URL).strip().rstrip("/")
    if not raw.startswith("http://") and not raw.startswith("https://"):
        if ":8443" in raw or ":443" in raw:
            raw = f"https://{raw}"
        elif ":8080" in raw or ":80" in raw:
            raw = f"http://{raw}"
        else:
            raw = f"https://{raw}"
    return raw

def _build_headers(token: Optional[str]) -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if token and token.strip():
        headers["X-Admin-Token"] = token.strip()
    return headers

def get_discovery_candidate_ips(hint_url: Optional[str] = None, config_path: Optional[str] = None) -> List[str]:
    """
    Builds a prioritized list of candidate IPs for discovery:
    1. Host from hint_url (if provided)
    2. Custom candidate IPs loaded from config (sungur.ini / /etc/etap-sungur-server.conf)
    3. Default known FATIH administrative network IPs
    4. Dynamically detected local subnet IPs
    """
    candidates: List[str] = []

    # 1. Host from hint_url if provided
    if hint_url:
        try:
            parsed = urllib.parse.urlparse(normalize_sungur_url(hint_url))
            host = parsed.hostname
            if host and host not in candidates:
                candidates.append(host)
        except Exception:
            pass

    # 2. Config file candidates (highest priority among defaults)
    cfg_ips = load_candidate_ips_from_config(config_path)
    for ip in cfg_ips:
        if ip not in candidates:
            candidates.append(ip)

    # 3. Known standard FATIH administrative network IPs
    for ip in DEFAULT_CANDIDATE_IPS:
        if ip not in candidates:
            candidates.append(ip)

    # 4. Dynamic local subnet heuristic for FATIH VLANs
    # NOTE (MEB): internal targets only; 8.8.8.8 is forbidden on MEB network.
    # UDP connect() sends no packets, just queries the routing table.
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        local_ip = ""
        for _target in (DEFAULT_CANDIDATE_IPS[0], "192.168.1.1", "10.0.0.1"):
            try:
                s.connect((_target, 80))
                local_ip = s.getsockname()[0]
                if local_ip and not local_ip.startswith("127."):
                    break
            except Exception:
                continue
        s.close()

        parts = local_ip.split(".")
        if len(parts) == 4:
            # If current machine is in 10.x.y.z (Interactive Board Network),
            # always probe standard Administrative Network IPs (192.168.0.x / 192.168.1.x)
            # because broadcast cannot cross VLAN boundaries!
            if parts[0] == "10":
                for admin_ip in ["192.168.0.67", "192.168.1.50", "192.168.0.50", "192.168.1.100"]:
                    if admin_ip not in candidates:
                        candidates.append(admin_ip)
            # If current machine is in Administrative Network (192.168.0.x - 192.168.7.x)
            elif parts[0] == "192" and parts[1] == "168":
                try:
                    third = int(parts[2])
                    if 0 <= third <= 7:  # Administrative subnet (192.168.0-7.*)
                        prefix = f"192.168.{third}"
                        for last in ["67", "50", "100", "1", "200"]:
                            cand = f"{prefix}.{last}"
                            if cand not in candidates and cand != local_ip:
                                candidates.append(cand)
                except Exception:
                    pass
    except Exception:
        pass

    return candidates

def _verify_http_endpoint(ip: str, port: int, is_https: bool, timeout: float = 0.8) -> bool:
    """Checks whether the Sungur /api/discovery/info endpoint responds on ip:port."""
    proto = "https" if is_https else "http"
    url = f"{proto}://{ip}:{port}/api/discovery/info"
    try:
        r = requests.get(url, timeout=timeout, verify=False)
        if r.status_code == 200:
            payload = r.json()
            if payload.get("service") in ("etap-sungur-server", "etap-fleet-server"):
                return True
        elif r.status_code in (401, 403):
            return True
    except Exception:
        pass
    return False

def _probe_udp_discovery(timeout: float = 1.2, hint_url: Optional[str] = None, config_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Probes the network via UDP broadcast and unicast on port 7889."""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(max(0.4, timeout))

        # Send broadcast probe
        try:
            sock.sendto(DISCOVERY_PROBE_PAYLOAD, ("255.255.255.255", DISCOVERY_UDP_PORT))
        except Exception:
            pass

        # Send unicast probe to candidates in case broadcast is blocked by switches
        candidates = get_discovery_candidate_ips(hint_url, config_path=config_path)
        for cand_ip in candidates:
            try:
                sock.sendto(DISCOVERY_PROBE_PAYLOAD, (cand_ip, DISCOVERY_UDP_PORT))
            except Exception:
                pass

        # Collect replies
        import time
        start_t = time.time()
        while time.time() - start_t < timeout:
            try:
                data, addr = sock.recvfrom(2048)
                text = data.decode("utf-8", errors="ignore").strip()
                if "etap-sungur-server" in text or "etap-fleet-server" in text:
                    info = json.loads(text)
                    ip = info.get("server_ip") or addr[0]
                    port = int(info.get("server_port", 8080))
                    https_port = info.get("server_https_port")

                    # If server specifically advertised an HTTPS port, try it first
                    if https_port and _verify_http_endpoint(ip, int(https_port), is_https=True):
                        return {
                            "url": f"https://{ip}:{https_port}",
                            "ip": ip,
                            "port": int(https_port),
                            "protocol": "https",
                            "service": info.get("service", "etap-sungur-server"),
                            "name": info.get("name", "ETAP Sungur"),
                            "source": "udp_discovery"
                        }

                    is_https = (port in (443, 8443))
                    if _verify_http_endpoint(ip, port, is_https=is_https):
                        proto = "https" if is_https else "http"
                        return {
                            "url": f"{proto}://{ip}:{port}",
                            "ip": ip,
                            "port": port,
                            "protocol": proto,
                            "service": info.get("service", "etap-sungur-server"),
                            "name": info.get("name", "ETAP Sungur"),
                            "source": "udp_discovery"
                        }
            except (socket.timeout, BlockingIOError):
                break
            except Exception:
                continue
    except Exception:
        pass
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass
    return None

def _probe_tcp_ports(hint_url: Optional[str] = None, timeout: float = 0.6, config_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Probes candidate IPs on standard Sungur ports (8443, 8080, 443, 80)."""
    candidates = get_discovery_candidate_ips(hint_url, config_path=config_path)
    for ip in candidates:
        for port in KNOWN_PROBE_PORTS:
            is_https = (port in (8443, 443))
            if _verify_http_endpoint(ip, port, is_https=is_https, timeout=timeout):
                proto = "https" if is_https else "http"
                return {
                    "url": f"{proto}://{ip}:{port}",
                    "ip": ip,
                    "port": port,
                    "protocol": proto,
                    "service": "etap-sungur-server",
                    "name": "ETAP Sungur Sunucusu",
                    "source": "tcp_port_probe"
                }
    return None

def discover_sungur_server(timeout: float = 2.0, hint_url: Optional[str] = None, config_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Discovers ETAP Sungur server IP and port on the local network.
    1. Probes UDP 7889 (broadcast + direct unicast to candidate IPs from config & defaults).
    2. Falls back to multi-port probing (8443, 8080, 443, 80) if UDP is blocked.
    Returns dictionary with url, ip, port, protocol, service, source or None.
    """
    # 1. UDP probe
    res = _probe_udp_discovery(timeout=min(1.2, timeout), hint_url=hint_url, config_path=config_path)
    if res:
        return res

    # 2. Multi-port probe fallback
    res = _probe_tcp_ports(hint_url=hint_url, timeout=0.6, config_path=config_path)
    if res:
        return res

    return None

def is_sungur_online(base_url: Optional[str] = None, timeout: float = 2.0) -> bool:
    """
    Fast and lightweight probe to check if Sungur server is reachable on the local network.
    Does not require authentication. Probes HTTPS first with fallback.
    """
    url = normalize_sungur_url(base_url)
    probe_url = f"{url}/api/discovery/info"
    try:
        r = requests.get(probe_url, timeout=timeout, verify=False)
        if r.status_code == 200:
            return True
        if r.status_code in (401, 403, 301, 302):
            return True
    except Exception:
        try:
            r2 = requests.get(f"{url}/", timeout=1.0, verify=False)
            if r2.status_code in (200, 401, 403):
                return True
        except Exception:
            # If default HTTPS fails, try HTTP fallback
            if base_url is None and url == DEFAULT_SUNGUR_URL:
                try:
                    r3 = requests.get(f"{FALLBACK_SUNGUR_URL}/api/discovery/info", timeout=1.0)
                    if r3.status_code in (200, 401, 403):
                        return True
                except Exception:
                    pass
            return False
    return False

def check_sungur_connection(base_url: str, token: Optional[str]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Checks if Sungur server is reachable and validates the admin token.
    Returns (ok, message, drift_summary).
    """
    url = normalize_sungur_url(base_url)
    endpoint = f"{url}/api/otp/drift-status"

    try:
        r = requests.get(endpoint, headers=_build_headers(token), timeout=8, verify=False)
    except requests.exceptions.ConnectionError:
        return False, f"Sungur sunucusuna ulaşılamadı ({url}). Sunucunun açık ve aynı yerel ağda olduğundan emin olun.", None
    except requests.exceptions.Timeout:
        return False, "Sungur sunucusundan yanıt zaman aşımına uğradı.", None
    except Exception as e:
        return False, f"Bağlantı hatası: {e}", None

    if r.status_code == 401:
        return False, "Yetkisiz erişim: Yönetici token'ı (X-Admin-Token) hatalı veya eksik.", None

    if r.status_code != 200:
        return False, f"Sunucu hata kodu döndürdü (HTTP {r.status_code}): {r.text[:200]}", None

    try:
        data = r.json().get("data", {})
        total = data.get("total_boards", 0)
        synced = data.get("synced_count", 0)
        drift = data.get("drift_count", 0)
        msg = f"Sungur bağlantısı başarılı! Toplam Tahta: {total} (Senkron: {synced}, Sapma/Eksik: {drift})"
        return True, msg, data
    except Exception:
        return True, "Sungur bağlantısı başarılı!", None

def deploy_otp_to_sungur(
    base_url: str,
    token: Optional[str],
    ebaid: str,
    username: str,
    secret: str,
    full_name: str,
    dry_run: bool = False
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Sends OTP deploy request to Sungur server.
    Returns (ok, message, full_result_dict).
    """
    url = normalize_sungur_url(base_url)
    endpoint = f"{url}/api/otp/deploy"

    payload = {
        "ebaid": ebaid,
        "username": username,
        "secret": secret,
        "full_name": full_name,
        "dry_run": dry_run
    }

    try:
        r = requests.post(endpoint, json=payload, headers=_build_headers(token), timeout=REQUEST_TIMEOUT, verify=False)
    except requests.exceptions.ConnectionError:
        return False, f"Sungur sunucusuna ulaşılamadı ({url}).", None
    except requests.exceptions.Timeout:
        return False, "Dağıtım isteği zaman aşımına uğradı. Tahtaların SSH bağlantısı yavaş olabilir.", None
    except Exception as e:
        return False, f"Dağıtım isteği gönderilemedi: {e}", None

    if r.status_code == 401:
        return False, "Yetkisiz erişim: Sungur yönetici token'ı geçersiz.", None

    if r.status_code != 200:
        detail = ""
        try:
            detail = r.json().get("detail", "")
        except Exception:
            detail = r.text[:200]
        return False, f"Sunucu hatası (HTTP {r.status_code}): {detail}", None

    try:
        resp_data = r.json()
        total = resp_data.get("total", 0)
        successful = resp_data.get("successful", 0)
        failed = resp_data.get("failed", 0)

        action_name = "Önizleme (Dry-Run)" if dry_run else "Dağıtım"
        summary = f"{action_name} tamamlandı: {successful}/{total} tahta başarılı"
        if failed > 0:
            summary += f" ({failed} tahta başarısız)"

        return True, summary, resp_data
    except Exception as e:
        return False, f"Sunucu cevabı çözümlenemedi: {e}", None
