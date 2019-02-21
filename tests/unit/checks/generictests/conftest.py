def pytest_addoption(parser):
    parser.addoption("--datasetfile", action="store", default="")


def pytest_generate_tests(metafunc):
    RuntimeError(repr(metafunc.config))
    # This is called for every test. Only get/set command line arguments
    # if the argument is specified in the list of test "fixturenames".
    for key, value in zip(('datasetfile',), (metafunc.config.option.datasetfile,)):
        if key in metafunc.fixturenames and value is not None:
            metafunc.parametrize(key, [value])
