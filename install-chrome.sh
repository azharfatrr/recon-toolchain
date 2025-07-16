#!/bin/bash

set -e

echo "[*] Uninstalling old Google Chrome and ChromeDriver..."
sudo apt remove -y google-chrome-stable || true
sudo rm -rf /usr/local/bin/chromedriver
sudo rm -rf /tmp/google-chrome* /tmp/chromedriver*

echo "[*] Installing latest Google Chrome..."
wget -q -N https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/google-chrome.deb
sudo apt install -y /tmp/google-chrome.deb

# Get installed Chrome version (e.g., 138.0.7204.100)
CHROME_VERSION=$(google-chrome --version | grep -oP '[0-9.]+')

echo "[+] Google Chrome version: $CHROME_VERSION"
echo "[*] Fetching matching ChromeDriver..."

# Construct download URL for ChromeDriver from Chrome for Testing
CHROMEDRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip"

wget -q -N "$CHROMEDRIVER_URL" -O /tmp/chromedriver.zip
unzip -q /tmp/chromedriver.zip -d /tmp/chromedriver

sudo cp /tmp/chromedriver/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver

sudo chmod +x /usr/local/bin/chromedriver
sudo chown "$USER":"$USER" /usr/local/bin/chromedriver

echo "[+] Installed ChromeDriver version:"
chromedriver -v
