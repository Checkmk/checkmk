import pytest
import cmk.render


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
    assert cmk.render.fmt_bytes(*entry) == result
