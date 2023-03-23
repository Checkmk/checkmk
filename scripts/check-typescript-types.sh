#!/usr/bin/env bash
set -e
echo "Check typescript with tsconfig.json"
npx --no tsc
echo "Check strict typescript with tsconfig.strict.json"
npx --no tsc -- --project tsconfig.strict.json
