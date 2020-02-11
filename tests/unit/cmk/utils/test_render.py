import pytest  # type: ignore[import]
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


@pytest.mark.parametrize("value, kwargs, result", [
    (10000486, {
        'precision': 5
    }, "10.00049 M"),
    (100000000, {
        'drop_zeroes': False
    }, "100.00 M"),
])
def test_fmt_number_with_precision(value, kwargs, result):
    assert cmk.utils.render.fmt_number_with_precision(value, **kwargs) == result


@pytest.mark.parametrize("entry, result", [(10000000, "10 Mbit/s"), (100000000, "100 Mbit/s"),
                                           (1000000000, "1 Gbit/s"), (1400, "1.4 kbit/s"),
                                           (8450, "8.45 kbit/s"), (26430, "26.43 kbit/s"),
                                           (8583000, "8.58 Mbit/s"), (7.84e9, "7.84 Gbit/s")])
def test_fmt_nic_speed(entry, result):
    assert cmk.utils.render.fmt_nic_speed(entry) == result
