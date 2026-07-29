"""Linker arguments selecting one static CRT flavour."""

_DYNAMIC_CRT_LIBS = [
    "msvcrt.lib",
    "msvcrtd.lib",
    "vcruntime.lib",
    "vcruntimed.lib",
    "ucrt.lib",
    "ucrtd.lib",
]

_STATIC_RELEASE_CRT_LIBS = [
    "libucrt.lib",
    "libvcruntime.lib",
    "libcmt.lib",
]

_STATIC_DEBUG_CRT_LIBS = [
    "libucrtd.lib",
    "libvcruntimed.lib",
    "libcmtd.lib",
]

def _crt_link_args(use, avoid):
    return ["/DEFAULTLIB:" + lib for lib in use] + \
           ["/NODEFAULTLIB:" + lib for lib in avoid + _DYNAMIC_CRT_LIBS]

RELEASE_CRT_LINK_ARGS = _crt_link_args(
    use = _STATIC_RELEASE_CRT_LIBS,
    avoid = _STATIC_DEBUG_CRT_LIBS,
)

DEBUG_CRT_LINK_ARGS = _crt_link_args(
    use = _STATIC_DEBUG_CRT_LIBS,
    avoid = _STATIC_RELEASE_CRT_LIBS,
)
