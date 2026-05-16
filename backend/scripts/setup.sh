#!/bin/bash

HF_TOKEN=$1

if [ -z "$HF_TOKEN" ]; then
    echo "Usage: ./setup.sh <huggingface_token>"
    exit 1
fi

export HF_TOKEN=$HF_TOKEN

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Downloading AI models..."
python scripts/download_models.py

echo "Setup complete."

