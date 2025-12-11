#!/bin/bash
cd "$(dirname "$0")"
git pull
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart binghome
echo "BingHome Hub updated successfully!"
