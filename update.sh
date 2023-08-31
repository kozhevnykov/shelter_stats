#!/bin/zsh

cd vps-logs--ua-1-1--2
git pull
cd ..
python3 shelter1v1_elo.py
echo "Done"

