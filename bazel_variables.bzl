"""Build variables including upstream mirror URL for external dependencies."""

UPSTREAM_MIRROR_URL = "https://artifacts.lan.tribe29.com/repository/upstream-archives/"

# Artifacts built and published by our own CI jobs, laid out like so:
# <publisher>/<name>/<version>/<platform>/<arch>/<variant>/<file>
CI_BINARY_ARTIFACTS_URL = "https://ci-binary-artifacts-710145618630-eu-central-1-an.s3.eu-central-1.amazonaws.com/dl/"
