#!/bin/bash
set -e

echo "Running AIOS tests..."

cd "$(dirname "$0")/.."

python3 tests/test_observer.py
python3 tests/test_context_engine.py
python3 tests/test_decision_engine.py
python3 tests/test_profile_store.py

echo "All tests passed"