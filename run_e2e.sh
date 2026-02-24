#!/bin/bash
cd "$(dirname "$0")/backend"
exec python tests/e2e_live_test.py
