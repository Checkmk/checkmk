#!/usr/bin/python
# encoding: utf-8

import pytest


# Override the global site fixture. Not wanted for git tests!
@pytest.fixture
def site(request):
    pass
