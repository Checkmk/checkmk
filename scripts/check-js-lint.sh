#!/usr/bin/env bash

npx --no eslint -- --max-warnings 0 --no-color '{enterprise/web,web}/htdocs/js/**/*.{j,t}s'
