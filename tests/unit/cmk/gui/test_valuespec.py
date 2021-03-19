# -*- encoding: utf-8 -*-

import pytest  # type: ignore[import]
from pathlib2 import Path

import cmk.gui.config
from cmk.gui.exceptions import MKUserError
import cmk.gui.valuespec as vs
from testlib import on_time
from cmk.gui.globals import html


@pytest.mark.parametrize("entry, result", [
    ("m0", ((1567296000.0, 1567702200.0), "September 2019")),
    ("m1", ((1564617600.0, 1567296000.0), "August 2019")),
    ("m3", ((1559347200.0, 1567296000.0), "June 2019 - August 2019")),
    ("y1", ((1514764800.0, 1546300800.0), "2018")),
    ("y0", ((1546300800.0, 1567702200.0), "2019")),
    ("4h", ((1567687800.0, 1567702200.0), u"Last 4 hours")),
    ("25h", ((1567612200.0, 1567702200.0), u"Last 25 hours")),
    ("8d", ((1567011000.0, 1567702200.0), u"Last 8 days")),
    ("35d", ((1564678200.0, 1567702200.0), u"Last 35 days")),
    ("400d", ((1533142200.0, 1567702200.0), u"Last 400 days")),
    ("d0", ((1567641600.0, 1567702200.0), u"Today")),
    ("d1", ((1567555200.0, 1567641600.0), u"Yesterday")),
    ("w0", ((1567382400.0, 1567702200.0), u"This week")),
    ("w1", ((1566777600.0, 1567382400.0), u"Last week")),
    (("date", (1536098400.0, 1567288800.0)),
     ((1536098400.0, 1567296000.0), "2018-09-04 ... 2019-09-01")),
    (("until", 1577232000), ((1567702200.0, 1577232000.0), u"2019-12-25")),
    (("time", (1549374782.0, 1567687982.0)),
     ((1549374782.0, 1567687982.0), "2019-02-05 ... 2019-09-05")),
    (("age", 2 * 3600), ((1567695000.0, 1567702200.0), u"The last 2 hours")),
    (("next", 3 * 3600), ((1567702200.0, 1567713000.0), u"The next 3 hours")),
])
def test_timerange(entry, result):
    with on_time("2019-09-05 16:50", "UTC"):
        assert vs.Timerange().compute_range(entry) == result


@pytest.mark.parametrize("entry, refutcdate, result", [
    ("m0", "2019-09-15 15:09", ((1567296000.0, 1568560140.0), "September 2019")),
    ("m1", "2019-01-12", ((1543622400.0, 1546300800.0), "December 2018")),
    ("m-1", "2019-09-15 15:09", ((1567296000.0, 1569888000.0), "September 2019")),
    ("m2", "2019-02-12", ((1543622400.0, 1548979200.0), "December 2018 - January 2019")),
    ("m3", "2019-02-12", ((1541030400.0, 1548979200.0), "November 2018 - January 2019")),
    ("m-3", "2019-02-12", ((1548979200.0, 1556668800.0), "February 2019 - April 2019")),
    ("m-3", "2018-12-12", ((1543622400.0, 1551398400.0), "December 2018 - February 2019")),
    ("m6", "2019-02-12", ((1533081600.0, 1548979200.0), "August 2018 - January 2019")),
    ("m-6", "2019-02-12", ((1548979200.0, 1564617600.0), "February 2019 - July 2019")),
    ("y0", "2019-09-15", ((1546300800.0, 1568505600.0), "2019")),
    ("y1", "2019-09-15", ((1514764800.0, 1546300800.0), "2018")),
    ("y-1", "2019-09-15", ((1546300800.0, 1577836800.0), "2019")),
])
def test_timerange2(entry, refutcdate, result):
    with on_time(refutcdate, "UTC"):
        assert vs.Timerange().compute_range(entry) == result


@pytest.mark.parametrize("args, result", [
    ((1546300800, 1, "m"), 1548979200),
    ((1546300800, 3, "m"), 1554076800),
    ((1546300800, -1, "m"), 1543622400),
    ((1546300800, -2, "m"), 1541030400),
    ((1546300800, -3, "m"), 1538352000),
    ((1538352000, 3, "m"), 1546300800),
    ((1546300800, -6, "m"), 1530403200),
])
def test_timehelper_add(args, result):
    with on_time("2019-09-05", "UTC"):
        assert vs.TimeHelper.add(*args) == result


@pytest.mark.parametrize(
    "address",
    [
        "user@localhost",
        "harri.hirsch@example.com",
        "!#$%&'*+-=?^_`{|}~@c.de",  # other printable ASCII characters
        u"user@localhost",
        u"harri.hirsch@example.com",
        u"!#$%&'*+-=?^_`{|}~@c.de",  # other printable ASCII characters
    ])
def test_email_validation(address):
    vs.EmailAddress().validate_value(address, "")


@pytest.mark.parametrize("address", [
    "a..b@c.de",
    "ab@c..de",
    u"a..b@c.de",
    u"ab@c..de",
])
def test_email_validation_non_compliance(address):
    # TODO: validate_value should raise an exception in these
    #       cases since subsequent dots without any ASCII
    #       character in between are not allowed in RFC5322.
    vs.EmailAddress().validate_value(address, "")


@pytest.mark.parametrize(
    "address",
    [
        "text",
        "user@foo",
        "\t\n a@localhost \t\n",  # whitespace is removed in from_html_vars
        "אሗ@test.com",  # UTF-8 encoded bytestring with non-ASCII characters
        u"text",
        u"user@foo",
        u"\t\n a@localhost \t\n",  # whitespace is removed in from_html_vars
        u"אሗ@test.de",  # non-ASCII characters
    ])
def test_email_validation_raises(address):
    with pytest.raises(MKUserError):
        vs.EmailAddress().validate_value(address, "")


@pytest.mark.parametrize(
    "address",
    [
        "user@localhost",
        "harri.hirsch@example.com",
        "!#$%&'*+-=?^_`{|}~@c.de",  # other printable ASCII characters
        u"user@localhost",
        u"harri.hirsch@example.com",
        u"!#$%&'*+-=?^_`{|}~@c.de",
        u"אሗ@test.de",  # non-ASCII characters
    ])
def test_unicode_email_validation(address):
    vs.EmailAddressUnicode().validate_value(address, "")


@pytest.mark.parametrize("address", [
    "a..b@c.de",
    "ab@c..de",
    u"a..b@c.de",
    u"ab@c..de",
])
def test_unicode_email_validation_non_compliance(address):
    # TODO: validate_value should raise an exception in these
    #       cases since subsequent dots without any ASCII
    #       character in between are not allowed in RFC5322.
    vs.EmailAddressUnicode().validate_value(address, "")


@pytest.mark.parametrize(
    "address",
    [
        "text",
        "user@foo",
        "\t\n a@localhost \t\n",  # whitespace is removed in from_html_vars
        "אሗ@test.com",  # UTF-8 encoded bytestrings are not allowed
        u"text",
        u"user@foo",
        u"\t\n a@localhost \t\n",  # whitespace is removed in from_html_vars
    ])
def test_unicode_email_validation_raises(address):
    with pytest.raises(MKUserError):
        vs.EmailAddressUnicode().validate_value(address, "")


@pytest.fixture()
def fixture_auth_secret():
    secret_path = Path(cmk.utils.paths.omd_root) / "etc" / "auth.secret"
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    with secret_path.open("wb") as f:
        f.write(b"auth-secret")


def test_password_from_html_vars_empty(register_builtin_html):
    html.request.set_var("pw_orig", "")
    html.request.set_var("pw", "")

    pw = vs.Password()
    assert pw.from_html_vars("pw") == ""


def test_password_from_html_vars_not_set(register_builtin_html):
    pw = vs.Password()
    assert pw.from_html_vars("pw") == ""


@pytest.mark.usefixtures("fixture_auth_secret")
def test_password_from_html_vars_initial_pw(register_builtin_html):
    html.request.set_var("pw_orig", "")
    html.request.set_var("pw", "abc")
    pw = vs.Password()
    assert pw.from_html_vars("pw") == "abc"


@pytest.mark.usefixtures("fixture_auth_secret")
def test_password_from_html_vars_unchanged_pw(register_builtin_html):
    html.request.set_var("pw_orig", vs.ValueEncrypter.encrypt("abc"))
    html.request.set_var("pw", "")
    pw = vs.Password()
    assert pw.from_html_vars("pw") == "abc"


@pytest.mark.usefixtures("fixture_auth_secret")
def test_password_from_html_vars_change_pw(register_builtin_html):
    html.request.set_var("pw_orig", vs.ValueEncrypter.encrypt("abc"))
    html.request.set_var("pw", "xyz")
    pw = vs.Password()
    assert pw.from_html_vars("pw") == "xyz"


@pytest.mark.usefixtures("fixture_auth_secret")
def test_value_encrypter_encrypt():
    encrypted = vs.ValueEncrypter.encrypt("abc")
    assert isinstance(encrypted, str)
    assert encrypted != "abc"


@pytest.mark.usefixtures("fixture_auth_secret")
def test_value_encrypter_transparent():
    enc = vs.ValueEncrypter
    assert enc.decrypt(enc.encrypt("abc")) == "abc"
