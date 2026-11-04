UPSTREAM_MIRROR_URL = "https://artifacts.lan.tribe29.com/repository/upstream-archives/"

# Only reachable from inside the company network, so used in CI only, see //:pypi_proxy.
PYPI_PROXY_INDEX_URL = "https://artifacts.lan.tribe29.com/repository/pypi-proxy/simple"

# uv arguments for installing from the Nexus PyPI proxy instead of pypi.org in CI, so
# pypi.org outages do not fail the venvs there.
UV_PYPI_PROXY_ARGS = select({
    "//:pypi_proxy_enabled": ["--default-index=" + PYPI_PROXY_INDEX_URL],
    "//conditions:default": [],
})

# uv pip install arguments for the venvs in CI. On top of the proxy, --no-deps skips
# resolving the dependencies again: the locks are complete, and resolving through the
# proxy is slow because it does not serve the wheel metadata separately (PEP 658).
UV_VENV_ARGS = UV_PYPI_PROXY_ARGS + select({
    "//:pypi_proxy_enabled": ["--no-deps"],
    "//conditions:default": [],
})

# TODO: Re-work this with edition_deps + check for duplicate in cmk/BUILD
edition_python_deps = {
    "cre": [],
    "cce": [
        "//non-free/packages/cmk-mknotifyd",
        "//non-free/packages/cmk-otel-collector",
    ],
    "cee": [
        "//non-free/packages/cmk-mknotifyd",
    ],
    "cme": [
        "//non-free/packages/cmk-mknotifyd",
        "//non-free/packages/cmk-otel-collector",
    ],
    "cse": [
        "//non-free/packages/cmk-mknotifyd",
        "//non-free/packages/cmk-otel-collector",
    ],
}

edition_deps = {
    "cre": [],
    "cce": [
        "//non-free/packages/cmk-mknotifyd:cmk_mknotifyd_pkg",
        "//non-free/packages/cmc-protocols:pkg_tar",
        "//non-free/packages/cmk-otel-collector:pkg_tar",
    ],
    "cee": [
        "//non-free/packages/cmk-mknotifyd:cmk_mknotifyd_pkg",
        "//non-free/packages/cmc-protocols:pkg_tar",
    ],
    "cme": [
        "//non-free/packages/cmk-mknotifyd:cmk_mknotifyd_pkg",
        "//non-free/packages/cmc-protocols:pkg_tar",
        "//non-free/packages/cmk-otel-collector:pkg_tar",
    ],
    "cse": [
        "//non-free/packages/cmk-mknotifyd:cmk_mknotifyd_pkg",
        "//non-free/packages/cmc-protocols:pkg_tar",
        "//non-free/packages/cmk-otel-collector:pkg_tar",
    ],
}

edition_skel_permissions = {
    "cce": [
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
    "cee": [
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
    "cme": [
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
    "cse": [
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
}
