#!/usr/bin/env bash
set -e

if [ "$EUID" -ne 0 ]; then
  echo "Bu betik root yetkisiyle çalıştırılmalıdır (sudo ./install-time-sync.sh)"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "1. etap-time-sync.sh /usr/local/sbin dizinine kopyalanıyor..."
cp "${SCRIPT_DIR}/etap-time-sync.sh" /usr/local/sbin/etap-time-sync.sh
chmod 755 /usr/local/sbin/etap-time-sync.sh
chown root:root /usr/local/sbin/etap-time-sync.sh

echo "2. etap-time-sync.service /etc/systemd/system dizinine kopyalanıyor..."
cp "${SCRIPT_DIR}/etap-time-sync.service" /etc/systemd/system/etap-time-sync.service
chmod 644 /etc/systemd/system/etap-time-sync.service
chown root:root /etc/systemd/system/etap-time-sync.service

echo "3. Servisler etkinleştiriliyor..."
systemctl daemon-reload
systemctl enable NetworkManager-wait-online.service || true
systemctl enable etap-time-sync.service

echo "4. Test çalıştırılıyor..."
systemctl start etap-time-sync.service
systemctl status etap-time-sync.service --no-pager

echo "✅ Kurulum tamamlandı! Tahta her açıldığında LightDM öncesi saat eşitlenecektir."
