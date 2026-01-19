#!/usr/bin/bash

# Validation script for migrating legacy checks to modern plugins
# This is convenient when using LLMs to assist with the migration, as
# the agent otherwise will keep
# a) forgetting to run some of the validation steps
# b) keep coming up with new commands that need approval

cd "$(git rev-parse --show-toplevel)" || exit 1

# shellcheck disable=SC2046  # we want word splitting here
bazel run //:format -- $(git diff --name-only) || exit 1

bazel lint --fix //cmk:lib_cmk_repo || exit 1

# run mypy on more than the changed files. Takes longer, but coming back later takes even more time.
scripts/run-uvenv mypy {tests/unit/,}cmk/base/{legacy_checks,check_legacy_includes} || exit 1

# ignore some that fail on collection.
scripts/run-uvenv pytest tests/unit/cmk/base/legacy_checks tests/unit/cmk/plugins/ \
    --ignore tests/unit/cmk/plugins/metric_backend/ \
    --ignore tests/unit/cmk/plugins/custom_query_metric_backend/ \
    --ignore tests/unit/cmk/plugins/clickhouse_omd/ \
    --ignore tests/unit/cmk/plugins/ceph || exit 1

make -C tests test-plugins-consistency
