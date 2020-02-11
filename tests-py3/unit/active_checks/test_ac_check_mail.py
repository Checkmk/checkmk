# -*- encoding: utf-8
# pylint: disable=protected-access,redefined-outer-name
import email
import pytest  # type: ignore[import]
from testlib import import_module  # pylint: disable=import-error


@pytest.fixture(scope="module")
def check_mail():
    return import_module("active_checks/check_mail")


def create_test_email(subject):
    email_string = 'Subject: %s\r\nContent-Transfer-Encoding: quoted-printable\r\nContent-Type: text/plain; charset="iso-8859-1"\r\n\r\nThe email content\r\nis very important!\r\n' % subject
    return email.message_from_string(email_string)


def test_ac_check_mail_main_failed_connect(check_mail):
    state, info, perf = check_mail.main(
        ['--server', 'foo', '--username', 'bar', '--password', 'baz'])
    assert state == 3
    assert info.startswith('Failed connect to foo:143:')
    assert perf is None


def test_ac_check_mail_main_successfully_connect(monkeypatch, check_mail):
    monkeypatch.setattr('check_mail.connect', lambda server, port, username, password, ssl: None)
    state, info, perf = check_mail.main(
        ['--server', 'foo', '--username', 'bar', '--password', 'baz'])
    assert state == 0
    assert info == 'Successfully logged in to mailbox'
    assert perf is None


@pytest.mark.parametrize("mails, expected_messages, expected_forwarded", [
    ({}, [], []),
    ({
        '1': create_test_email("Foobar"),
    }, [
        ('<21>', 'None Foobar: Foobar|The email content\x00is very important!\x00'),
    ], [
        '1',
    ]),
    ({
        '2': create_test_email("Bar"),
        '1': create_test_email("Foo"),
    }, [
        ('<21>', 'None Foo: Foo|The email content\x00is very important!\x00'),
        ('<21>', 'None Bar: Bar|The email content\x00is very important!\x00'),
    ], [
        '1',
        '2',
    ]),
])
def test_ac_check_mail_prepare_messages_for_ec(check_mail, mails, expected_messages,
                                               expected_forwarded):
    # Use default parameters
    messages, forwarded = check_mail.prepare_messages_for_ec(mails, None, None, 16, '', None, 1000)
    assert forwarded == expected_forwarded
    for message, (expected_priority, expected_message) in zip(messages, expected_messages):
        assert message.startswith(expected_priority)
        assert message.endswith(expected_message)
