FROM shimizukawa/python-all-dev

ENV LC_ALL=C.UTF-8 LANG=C.UTF-8

ARG PYTHON_VERSION

# We need gcc for building psutil
RUN apt-get update && apt-get install -y gcc
# TODO: We should find a common place for all dependencies we're needing for our agent plugins to work and then include those dependencies here.
RUN \
    if [ "$PYTHON_VERSION" = "2.6" ] || [ "$PYTHON_VERSION" = "3.4" ] || [ "$PYTHON_VERSION" = "3.3" ]; then \
        GET_PIP_URL="https://bootstrap.pypa.io/$PYTHON_VERSION/get-pip.py" ; \
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
    pip$PYTHON_VERSION install psutil pytest pytest-mock mock requests "$PYMONGO"
