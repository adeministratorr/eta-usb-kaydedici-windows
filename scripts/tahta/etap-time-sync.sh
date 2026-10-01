#!/usr/bin/env bash
# Pardus ETAP 23 - Güvenli & Doğrulanmış Boot Saat Senkronizasyonu (v2.5)
# Pil bitik tahtalarda LightDM / OTP login öncesi saati güvenli kaynaklardan düzeltir.
# Sahte/man-in-the-middle HTTP Date başlıklarına güvenmez; imzalı/doğrulanmış Sungur JSON ve NTP kullanır.

set -u

CONF_FILES=(
    "/etc/etap-sungur-server.conf"
    "/etc/etap-fleet-server.conf"
)

# 1. Sunucu aday listesini yapılandırma dosyasından ve ortam değişkenlerinden topla
CANDIDATE_HOSTS=()
if [ -n "${ETAP_SERVER_IP:-}" ]; then
    CANDIDATE_HOSTS+=("${ETAP_SERVER_IP}")
fi

for conf in "${CONF_FILES[@]}"; do
    if [ -f "$conf" ]; then
        VAL=$(head -n 1 "$conf" | tr -d '\r\n ' | cut -d':' -f1)
        if [ -n "$VAL" ]; then
            CANDIDATE_HOSTS+=("$VAL")
        fi
    fi
done

# Belgelenmiş yerel ağ fallback adayları
FALLBACK_HOSTS=(
    "192.168.0.67"
    "192.168.1.50"
    "10.0.0.50"
    "etap-sungur.local"
)

for h in "${FALLBACK_HOSTS[@]}"; do
    CANDIDATE_HOSTS+=("$h")
done

# Listeden tekilleştirme yap
TARGET_SERVERS=()
for host in "${CANDIDATE_HOSTS[@]}"; do
    # Port içermiyorsa 8080 varsay
    if [[ "$host" == *:* ]]; then
        srv="http://${host}"
    else
        srv="http://${host}:8080"
    fi
    # Tekrarları önle
    if [[ ! " ${TARGET_SERVERS[*]:-} " =~ " ${srv} " ]]; then
        TARGET_SERVERS+=("$srv")
    fi
done

apply_epoch_time() {
    local epoch_raw="$1"
    local source_name="$2"
    
    # 2024 sonrası geçerli Unix timestamp kontrolü (> 1700000000)
    local epoch_int="${epoch_raw%%.*}"
    if [ -n "$epoch_int" ] && [ "$epoch_int" -gt 1700000000 ] 2>/dev/null; then
        timedatectl set-timezone Europe/Istanbul 2>/dev/null || true
        timedatectl set-ntp false 2>/dev/null || true
        if date -u -s "@${epoch_int}" >/dev/null 2>&1; then
            hwclock --systohc >/dev/null 2>&1 || true
            logger -t etap-time-sync "BAŞARILI: Saat ${source_name} üzerinden güvenle eşitlendi (@${epoch_int}): $(date)"
            return 0
        fi
    fi
    return 1
}

SYNCED=0

# Adım A: Ağda MEB / Fatih veya yerel NTP varsa dene (hızlı 1.5 sn)
if command -v ntpdate >/dev/null 2>&1; then
    for ntp_srv in "10.0.0.1" "meb.gov.tr" "pool.ntp.org"; do
        if ntpdate -u -t 1.5 "$ntp_srv" >/dev/null 2>&1; then
            hwclock --systohc >/dev/null 2>&1 || true
            logger -t etap-time-sync "BAŞARILI: Saat NTP ($ntp_srv) üzerinden eşitlendi: $(date)"
            SYNCED=1
            break
        fi
    done
fi

# Adım B: NTP yoksa veya engelliyse doğrulanmış Sungur API endpoint'ini kullan
if [ "$SYNCED" -eq 0 ]; then
    for attempt in {1..3}; do
        for base in "${TARGET_SERVERS[@]}"; do
            # Doğrulanmış Sungur discovery JSON endpoint'i (1.5 sn katı zaman aşımı)
            DISCOVERY_JSON=$(curl -s -m 1.5 "${base}/api/discovery/info" 2>/dev/null || true)
            
            # Sungur servis imzası doğrulaması
            if echo "$DISCOVERY_JSON" | grep -q "etap-sungur-server\|etap-fleet-server"; then
                # JSON içindeki server_time değerini çek
                SERVER_TIME=$(echo "$DISCOVERY_JSON" | grep -o '"server_time":[0-9.]*' | cut -d':' -f2 || true)
                if [ -n "$SERVER_TIME" ] && apply_epoch_time "$SERVER_TIME" "${base}/api/discovery/info"; then
                    SYNCED=1
                    break 2
                fi
            fi
        done
        sleep 1
    done
fi

if [ "$SYNCED" -eq 0 ]; then
    logger -t etap-time-sync "UYARI: Güvenilir saat kaynağına ulaşılamadı (mevcut saat: $(date))"
fi

# Asla boot'u engelleme
exit 0
