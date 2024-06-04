#!/bin/zsh

cd vps-logs--ua-1-1--2
git pull
cd ..
cd 1x1elo
python3 main.py
echo "Done"

