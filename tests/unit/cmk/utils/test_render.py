import pytest
import cmk.utils.render


@pytest.mark.parametrize("entry, result", [
    ((5,), "5.00 B"),
    ((5, 1000, False), "5 B"),
    ((2300,), "2.25 kB"),
    ((-2300,), "-2.25 kB"),
    ((3e6,), "2.86 MB"),
    ((3e6, 1000, 2, "B"), "3.00 MB"),
    ((4e9,), "3.73 GB"),
    ((-5e12,), "-4.55 TB"),
    ((6e15,), "5.33 PB"),
])
def test_fmt_bytes(entry, result):
    assert cmk.utils.render.fmt_bytes(*entry) == result


@pytest.mark.parametrize("args, result", [((0.433 / 1, 10), (4.33, -1)), ((5, 10), (5, 0))])
def test_frexpb(args, result):
    assert cmk.utils.render._frexpb(*args) == result
