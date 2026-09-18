#!/bin/bash
cd /mnt/c/Users/TransOrg/Documents/Outbound
source .venv-tts/bin/activate
export PYTHONIOENCODING=utf-8
python tools/prerender_audio.py --engine parler --locales bn ta te kn ml
