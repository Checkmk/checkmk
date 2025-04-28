ARG PYTHON_VERSION_MAJ_MIN
ARG DOCKER_REGISTRY

# COPY --from cannot deal with ARGs (or I was not able to...). So use a multistage build and use slim later
FROM ${DOCKER_REGISTRY}/python:3.9-slim as slim
FROM ${DOCKER_REGISTRY}/python:${PYTHON_VERSION_MAJ_MIN}

# Yes, really again the same ARG: https://ryandaniels.ca/blog/docker-dockerfile-arg-from-arg-trouble/
ARG PYTHON_VERSION_MAJ_MIN

ENV DEBIAN_FRONTEND=noninteractive LC_ALL=C.UTF-8 LANG=C.UTF-8 PATH="/opt/bin:${PATH}"

# conditional copy magic. Similar to || true in bash
# https://redgreenrepeat.com/2018/04/13/how-to-conditionally-copy-file-in-dockerfile/
COPY --from=slim /usr/local/lib/python3.9/distutils optional_file* /usr/lib/python3.9/distutils

RUN \
    if [ "$PYTHON_VERSION_MAJ_MIN" = "2.7" ] || [ "$PYTHON_VERSION_MAJ_MIN" = "3.4" ] || [ "$PYTHON_VERSION_MAJ_MIN" = "3.5" ] || [ "$PYTHON_VERSION_MAJ_MIN" = "3.6" ] || [ "$PYTHON_VERSION_MAJ_MIN" = "3.7" ] || [ "$PYTHON_VERSION_MAJ_MIN" = "3.8" ]; then \
        GET_PIP_URL="https://bootstrap.pypa.io/pip/$PYTHON_VERSION_MAJ_MIN/get-pip.py" ; \
    else \
    GET_PIP_URL="https://bootstrap.pypa.io/get-pip.py" ; \
    fi && \
    if [ "$PYTHON_VERSION_MAJ_MIN" = "3.4" ]; then \
    PYMONGO="pymongo==3.12" ; \
    else \
    PYMONGO="pymongo" ; \
    fi && \
    python3 -c "import urllib.request ; urllib.request.urlretrieve('$GET_PIP_URL', '/get-pip.py')" && \
    python$PYTHON_VERSION_MAJ_MIN /get-pip.py --target $(python$PYTHON_VERSION_MAJ_MIN -c 'import sys; print(sys.path[-1])') && \
    python$PYTHON_VERSION_MAJ_MIN -m pip install pytest pytest-mock mock requests "$PYMONGO" --target $(python$PYTHON_VERSION_MAJ_MIN -c 'import sys; print(sys.path[-1])') && \
    # In python 3.4, it seemes we need to have typing installed in order to run pytest
    # As typing is ignored during run-time, this should not introduce a dependencies for the host envs
    if [ "$PYTHON_VERSION_MAJ_MIN" = "3.4" ]; then \
    python$PYTHON_VERSION_MAJ_MIN -m pip  install typing; \
    fi \
