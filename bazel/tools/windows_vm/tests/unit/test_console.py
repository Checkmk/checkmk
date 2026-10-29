# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
import threading
import time
from collections.abc import Sequence

import pytest
from qemu_windows.console import attach, ConsoleError, Keys, login, SizeQueries

# Screens as SAC and cmd send them (shortened), NULs included.
SWITCH = (
    b"\x1b[2J\x1b[1;1HName:                  SAC\r\nUse any other key to view this channel.\r\n"
)
SAC_SCREEN = b"\x1b[2J\x1b[1;1H\x1b[9;1HSAC>   \x1b[24;1H         \x1b[9;5H\x1b[37m"
# SAC's screen after earlier logins, in two writes: its history, past a
# first prompt and down to its colored last row, names their channels.
SAC_SCREEN_AFTER_LOGIN = (
    b"\x1b[2J\x1b[1;1H\x1b[9;1HSAC>   ",
    (
        b"\x1b[22;1HChannel: Cmd0001  \x1b[23;1HSAC>ch -sn Cmd0001\x1b[0m"
        b"\x1b[24;1H\x1b[40m\x1b[37mSAC>\x1b[0m\x1b[0m\x1b[24;5H\x1b[22m"
    ),
)
CMD_AVAILABLE = b"\x1b[10;1HEVENT: The CMD command is now available.     \x1b[11;1HSAC>  "
CHANNEL_CREATED = (
    b"\x1b[8;1HThe Command Prompt session was successfully launched.  \x1b[9;1HSAC>   "
    b'\x1b[10;1HEVENT:   A new channel has been created.  Use "ch -?" for channel help.'
    b"\x1b[11;1HChannel: Cmd0"
)
SIZE_QUERY = b"\x1b[18t"
# The answer for SAC's screen.
SAC_SIZE_ANSWER = b"\x1b[8;24;80t"
CMD_SCREEN = (
    b"\x1b[2J\x1b[m\x1b[HMicrosoft Windows [Version 10.0.20348.587]\x1b]0;"
    b"C:\\Windows\\system32\\cmd.exe\x07\x1b[3;1H\r\nC:\\Windows\\system32>"
)
# The same screen, its prompt after the window's title.
CMD_SCREEN_TITLED = (
    b"\x1b[2J\x1b[m\x1b[H\x1b[?25hMicrosoft Windows [Version 10.0.20348.587]\r\n\r\n"
    b"\x1b]0;Administrator: C:\\Windows\\system32\\cmd.exe\x07C:\\Windows\\system32>"
)
# The same screen, its prompt placed by moving the cursor.
CMD_SCREEN_ADDRESSED = (
    b"\x1b[2J\x1b[m\x1b[H\r\n\r\n\x1b[H\x1b]0;C:\\Windows\\system32\\cmd.exe\x07"
    b"Microsoft Windows [Version 10.0.20348.587]\r\n(c) Microsoft Corporation.\x1b[4;1H"
    b"C:\\Windows\\system32>\x1b]0;Administrator: C:\\Windows\\system32\\cmd.exe\x07"
)
PS_PROMPT = b"\x1b]0;Administrator: powershell\x07PS C:\\> "
# A logged-in session's screen as the console host redraws it on a switch.
SESSION_SCREEN = (
    b"\x1b[18t\x1b[?25l\x1b[HMicrosoft Windows [Version 10.0.20348.587]\x1b[K\r\n"
    b"PS C:\\>\x1b[K\r\n\x1b[K\x1b[7;9H\x1b[?25h"
)

# Each input and the answer to it, in one write or several.
Script = Sequence[tuple[bytes, bytes | tuple[bytes, ...]]]


def until_sac(screen: bytes | tuple[bytes, ...] = SAC_SCREEN) -> Script:
    return [(b"\x1b\t0", SWITCH), (b"\r", screen)]


def echo(line: bytes) -> tuple[bytes, bytes]:
    """cmd's echo of line, with the console host's escapes in it, moving to
    the next prompt by the cursor."""
    middle = len(line) // 2
    return line + b"\r", (
        line[:middle] + b"\x1b[?25l" + line[middle:] + b"\x1b[7;1HC:\\Windows\\system32>"
    )


# cmd took the first line typed after its prompt.
SYNCED = (echo(b"rem sync 1"),)
# A redraw after the prompt dropped the start of the first line typed.
REDRAWN = (
    (b"rem sync 1\r", b"\x1b[HMicrosoft Windows\x1b[4;1HC:\\Windows\\system32>sync 1\x1b[K"),
    echo(b"rem sync 2"),
)


def from_channel(channel: bytes, cmd_screen: bytes = CMD_SCREEN, sync: Script = SYNCED) -> Script:
    """SAC's answers from the new channel on; SAC sends its name in two
    parts."""
    return [
        (b"cmd\r", CHANNEL_CREATED + channel[4:]),
        (b"ch -sn " + channel + b"\r", SWITCH.replace(b"SAC", channel)),
        (b"\r", b"\r\nPlease enter login credentials.\r\n\x00Username: \x00"),
        (b"Administrator\r", b"Administrator\r\nDomain  : \x00"),
        (b"\r", b"\r\nPassword: \x00"),
        # The console host shows its screen once the terminal has told it
        # its size.
        (b"QemuRunner1!\r", b"************\r\nAttempting to authenticate...\r\n" + SIZE_QUERY),
        (SAC_SIZE_ANSWER, cmd_screen),
        *sync,
        (b'DeleteChar" & exit\r', PS_PROMPT),
    ]


def fake_console(script: Script) -> socket.socket:
    """The client end of a console that answers each input of script, in
    order, once it has arrived; the writes of an answer 0.1 s apart."""
    ours, theirs = socket.socketpair()

    def serve() -> None:
        with theirs:
            received = b""
            for expected, answer in script:
                while expected not in received:
                    if not (data := theirs.recv(4096)):
                        return
                    received += data
                received = received[received.index(expected) + len(expected) :]
                for i, part in enumerate((answer,) if isinstance(answer, bytes) else answer):
                    if i:
                        time.sleep(0.1)
                    theirs.sendall(part)
            while theirs.recv(4096):
                pass

    threading.Thread(target=serve, daemon=True).start()
    return ours


@pytest.mark.parametrize(
    "cmd_screen",
    [
        pytest.param(CMD_SCREEN, id="after-new-lines"),
        pytest.param(CMD_SCREEN_TITLED, id="after-the-window-title"),
        pytest.param(CMD_SCREEN_ADDRESSED, id="placed-by-the-cursor"),
    ],
)
def test_login_finds_cmds_prompt_however_the_console_host_places_it(cmd_screen: bytes) -> None:
    with fake_console([*until_sac(), *from_channel(b"Cmd0001", cmd_screen)]) as sock:
        assert login(sock, timeout=5) == b"Cmd0001"


def test_login_types_again_when_a_redraw_drops_the_first_line() -> None:
    with fake_console([*until_sac(), *from_channel(b"Cmd0001", sync=REDRAWN)]) as sock:
        assert login(sock, timeout=5) == b"Cmd0001"


def test_login_switches_to_the_new_channel_not_one_in_sacs_history() -> None:
    with fake_console([*until_sac(SAC_SCREEN_AFTER_LOGIN), *from_channel(b"Cmd0002")]) as sock:
        assert login(sock, timeout=5) == b"Cmd0002"


def test_login_sends_cmd_again_when_sac_drops_it() -> None:
    with fake_console([*until_sac(), (b"cmd\r", CMD_AVAILABLE), *from_channel(b"Cmd0001")]) as sock:
        assert login(sock, timeout=5, retry=0.2) == b"Cmd0001"


def test_login_without_a_cmd_channel_says_so() -> None:
    with (
        fake_console(until_sac()) as sock,
        pytest.raises(ConsoleError, match="SAC's cmd channel is not available"),
    ):
        login(sock, timeout=1, retry=0.2)


def test_attach_without_the_session_says_so() -> None:
    script = [
        *until_sac(),
        (b"ch -sn Cmd0001\r", b"\r\nError: Could not find a channel with that name.\r\nSAC>"),
    ]
    with (
        fake_console(script) as sock,
        pytest.raises(ConsoleError, match="no channel Cmd0001"),
    ):
        attach(sock, SizeQueries(), timeout=5)


# A switch after which the console host does not redraw its screen.
NOT_REDRAWN = [
    *until_sac(),
    (b"ch -sn Cmd0001\r", SWITCH.replace(b"SAC", b"Cmd0001")),
    (b"\r", b".\r\n"),
]


def test_attach_switches_again_when_the_screen_is_not_redrawn() -> None:
    script = [
        *NOT_REDRAWN,
        *until_sac(),
        (b"ch -sn Cmd0001\r", SWITCH.replace(b"SAC", b"Cmd0001")),
        (b"\r", SESSION_SCREEN),
    ]
    with fake_console(script) as sock:
        assert attach(sock, SizeQueries(), timeout=5, redraw=0.3).endswith(b"\x1b[7;9H\x1b[?25h")


def test_attach_clears_the_screen_when_no_switch_redraws_it() -> None:
    # Ctrl-L, not Enter: the line typed so far stays unrun.
    script = [*NOT_REDRAWN, *NOT_REDRAWN, (b"\x0c", b"\x1b[2J\x1b[HPS C:\\> ls")]
    with fake_console(script) as sock:
        assert attach(sock, SizeQueries(), timeout=5, redraw=0.3, tries=2) == (
            b"\x1b[2J\x1b[HPS C:\\> ls"
        )


def test_size_query_is_answered_and_not_shown() -> None:
    assert SizeQueries().feed(b"PS C:\\>\x1b[18t ") == (b"PS C:\\> ", SAC_SIZE_ANSWER)


def test_size_query_is_answered_with_the_size_at_the_time() -> None:
    size = [24, 80]
    queries = SizeQueries(lambda: (size[0], size[1]))
    size[:] = [40, 146]
    assert queries.feed(b"\x1b[18t") == (b"", b"\x1b[8;40;146t")


def test_size_query_split_over_two_reads_is_answered_once() -> None:
    queries = SizeQueries()
    first = queries.feed(b"PS C:\\>\x1b[1")
    assert (first, queries.feed(b"8t ")) == ((b"PS C:\\>", b""), (b" ", SAC_SIZE_ANSWER))


def test_other_escape_that_starts_like_a_size_query_is_shown_whole() -> None:
    queries = SizeQueries()
    first = queries.feed(b"x\x1b[1")
    assert (first, queries.feed(b"0m")) == ((b"x", b""), (b"\x1b[10m", b""))


def test_cursor_key_becomes_the_control_key_the_session_binds() -> None:
    assert Keys().feed(b"ab\x1b[D") == b"ab\x02"


def test_cursor_key_in_application_mode_becomes_the_same_control_key() -> None:
    assert Keys().feed(b"\x1bOD") == b"\x02"


def test_cursor_key_split_over_two_reads_becomes_one_control_key() -> None:
    keys = Keys()
    first = keys.feed(b"ab\x1b[")
    assert (first, keys.feed(b"3~c")) == (b"ab", b"\x04c")
