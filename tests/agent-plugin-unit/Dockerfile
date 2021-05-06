FROM shimizukawa/python-all-dev

ENV LC_ALL=C.UTF-8 LANG=C.UTF-8

ARG PYTHON_VERSION

RUN \
    if [ "$PYTHON_VERSION" = "2.7" ] || [ "$PYTHON_VERSION" = "2.6" ] || [ "$PYTHON_VERSION" = "3.4" ] || [ "$PYTHON_VERSION" = "3.3" ]; then \
        GET_PIP_URL="https://bootstrap.pypa.io/pip/$PYTHON_VERSION/get-pip.py" ; \
    elif [ "$PYTHON_VERSION" = "3.5" ]; then \
        GET_PIP_URL="https://bootstrap.pypa.io/pip/3.4/get-pip.py" ; \
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
    python$PYTHON_VERSION /get-pip.py && \
    pip$PYTHON_VERSION install pytest pytest-mock mock requests "$PYMONGO" && \
    # In python 3.4, it seemes we need to have typing installed in order to run pytest
    # As typing is ignored during run-time, this should not introduce a dependencies for the host envs
    if [ "$PYTHON_VERSION" = "3.4" ]; then \
        pip$PYTHON_VERSION install typing; \
    fi \
