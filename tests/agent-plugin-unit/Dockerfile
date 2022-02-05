FROM ubuntu:18.04

ARG PYTHON_VERSION

ENV DEBIAN_FRONTEND=noninteractive LC_ALL=C.UTF-8 LANG=C.UTF-8 PATH="/opt/bin:${PATH}"

RUN : \
    && apt-get update -qqqq \
    && apt-get install -yqqqq \
    software-properties-common

RUN : \
    && add-apt-repository ppa:deadsnakes \
    && apt-get install -yqqqq --no-install-recommends \
    python$PYTHON_VERSION \
    python3-distutils \
    && apt-get clean \
    && rm -rf /var/cache/apt/archives/* /var/lib/apt/lists/*

# conditional copy magic. Similar to || true in bash
# https://redgreenrepeat.com/2018/04/13/how-to-conditionally-copy-file-in-dockerfile/
COPY --from=python:3.9-slim /usr/local/lib/python3.9/distutils optional_file* /usr/lib/python3.9/distutils

RUN \
    if [ "$PYTHON_VERSION" = "2.7" ] || [ "$PYTHON_VERSION" = "2.6" ] || [ "$PYTHON_VERSION" = "3.3" ] || [ "$PYTHON_VERSION" = "3.4" ] || [ "$PYTHON_VERSION" = "3.5" ] || [ "$PYTHON_VERSION" = "3.6" ]; then \
        GET_PIP_URL="https://bootstrap.pypa.io/pip/$PYTHON_VERSION/get-pip.py" ; \
    else \
    GET_PIP_URL="https://bootstrap.pypa.io/get-pip.py" ; \
    fi && \
    if [ "$PYTHON_VERSION" = "2.6" ]; then \
    PYMONGO="pymongo==3.7.2" ; \
    elif [ "$PYTHON_VERSION" = "3.3" ]; then \
    PYMONGO="pymongo==3.5.1" ; \
    else \
    PYMONGO="pymongo" ; \
    fi && \
    python3 -c "import urllib.request ; urllib.request.urlretrieve('$GET_PIP_URL', '/get-pip.py')" && \
    python$PYTHON_VERSION /get-pip.py --target $(python$PYTHON_VERSION -c 'import sys; print(sys.path[-1])') && \
    python$PYTHON_VERSION -m pip install pytest pytest-mock mock requests "$PYMONGO" --target $(python$PYTHON_VERSION -c 'import sys; print(sys.path[-1])') && \
    # In python 3.4, it seemes we need to have typing installed in order to run pytest
    # As typing is ignored during run-time, this should not introduce a dependencies for the host envs
    if [ "$PYTHON_VERSION" = "3.4" ]; then \
    python$PYTHON_VERSION -m pip  install typing; \
    fi \
