FROM shimizukawa/python-all

ENV LC_ALL=C.UTF-8 LANG=C.UTF-8

ARG PYTHON_VERSION
RUN \
    if [ "$PYTHON_VERSION" = "2.6" ]; then \
        GET_PIP_URL="https://bootstrap.pypa.io/$PYTHON_VERSION/get-pip.py" ; \
        PYMONGO="pymongo==3.7.2" ; \
    else \
        GET_PIP_URL="https://bootstrap.pypa.io/get-pip.py" ; \
        PYMONGO="pymongo" ; \
    fi && \
    python3 -c "import urllib.request ; urllib.request.urlretrieve('$GET_PIP_URL', '/get-pip.py')" && \
    python$PYTHON_VERSION /get-pip.py && \
    pip$PYTHON_VERSION install pytest pytest-mock requests "$PYMONGO"
