"""Build variables including upstream mirror URL for external dependencies."""

UPSTREAM_MIRROR_URL = "https://artifacts.lan.tribe29.com/repository/upstream-archives/"

# Artifacts built and published by our own CI jobs, laid out like so:
# <publisher>/<name>/<version>/<platform>/<arch>/<variant>/<file>
CI_BINARY_ARTIFACTS_URL = "https://ci-binary-artifacts-710145618630-eu-central-1-an.s3.eu-central-1.amazonaws.com/dl/"

# The Nexus PyPI proxy, only reachable from inside the company network. CI sets
# //:pip_index_url to it (see bazel/rc/ci.rc), which //:pypi_proxy_enabled matches.
PYPI_PROXY_INDEX_URL = "https://artifacts.lan.tribe29.com/repository/pypi-proxy/simple"

# uv pip compile arguments for the requirement locks: the defaults of rules_uv without
# --emit-index-url, so the locks stay the same whichever index they are resolved against,
# and resolved through the Nexus PyPI proxy in CI, so pypi.org outages do not fail the
# lock checks there.
UV_PIP_COMPILE_ARGS = [
    "--generate-hashes",
    "--no-strip-extras",
] + select({
    "//:pypi_proxy_enabled": ["--default-index=" + PYPI_PROXY_INDEX_URL],
    "//conditions:default": [],
})
