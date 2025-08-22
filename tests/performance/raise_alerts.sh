#!/usr/bin/env bash
_GIT_ROOT=$(git rev-parse --show-toplevel)
_BRANCH=$(make --no-print-directory --file="${_GIT_ROOT}/defines.make" print-BRANCH_VERSION)
_EDITION=cee
_RELEASES=()
for ((i = -5; i <= 0; i++)); do
    _RELEASES+=("${_BRANCH}-$(date -d "$i days" +"%Y.%m.%d").${_EDITION}")
done
_DAILY_RELEASE=${_BRANCH}-$(date +"%Y.%m.%d").${_EDITION}
"${_GIT_ROOT}/tests/performance/perftest_plot.py" "${_RELEASES[@]}" --dbhost=qa.lan.checkmk.net --validate-baselines --alert-on-failure "${@}"
