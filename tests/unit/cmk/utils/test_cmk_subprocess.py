# -*- encoding: utf-8; py-indent-offset: 4 -*-
import pytest  # type: ignore[import]
import six
import cmk.utils.cmk_subprocess as subprocess


def _check_type_of_stdout_and_stderr(p_communicate, encoding):
    stdout, stderr = p_communicate
    if stdout:
        if encoding:
            assert isinstance(stdout, six.text_type)
        else:
            assert isinstance(stdout, six.binary_type)
    if stderr:
        if encoding:
            assert isinstance(stdout, six.text_type)
        else:
            assert isinstance(stdout, six.binary_type)


@pytest.mark.parametrize("command, encoding", [
    (['ls'], None),
    (['ls'], "utf-8"),
])
def test_cmk_subprocess_no_input(command, encoding):
    p = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding=encoding,
    )
    _check_type_of_stdout_and_stderr(p.communicate(), encoding)


@pytest.mark.parametrize("command, input_, encoding", [
    (['grep', 'f.*'], b'foo', None),
    (['grep', 'f.*'], b'f\xc3\xb6\xc3\xb6', None),
    (['grep', 'f.*'], u'foo', "utf-8"),
    (['grep', 'f.*'], u'föö', "utf-8"),
])
def test_cmk_subprocess_input_no_errors(command, input_, encoding):
    p = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding=encoding,
    )
    _check_type_of_stdout_and_stderr(p.communicate(), encoding)


@pytest.mark.parametrize("command, input_, encoding, py3_error", [
    (['grep', 'f.*'], b'foo', "utf-8", AttributeError),
    (['grep', 'f.*'], b'f\xc3\xb6\xc3\xb6', "utf-8", AttributeError),
    (['grep', 'f.*'], u'foo', None, TypeError),
    (['grep', 'f.*'], u'föö', None, TypeError),
])
def test_cmk_subprocess_input_errors(command, input_, encoding, py3_error):
    p = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding=encoding,
    )
    # from Python 3 subprocess:
    #   AttributeError: 'bytes' object has no attribute 'encode'
    #   TypeError: memoryview: a bytes-like object is required, not 'str'
    with pytest.raises(py3_error):
        p.communicate(input_)
