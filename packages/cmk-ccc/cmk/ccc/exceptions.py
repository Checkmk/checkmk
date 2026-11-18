#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared exception types. Legacy: do not extend, do not imitate.

WARNING: This module is a design we are moving away from.

If possible:
* Do not add exceptions to this module.
* Do not derive new exceptions from the ones defined here.
* Do not add new `raise` or `except` sites for them.
  There almost always is an alternative, see below.

These classes are used all over the code base. That is the problem this text
describes, not a recommendation.


Why a shared exception module is a problem
==========================================

1. Exceptions are part of an interface, and this module takes them away from
   their owner.

   What a function raises belongs to its contract just like what it returns.
   A type defined here, at the very bottom of the dependency graph, is owned by
   no interface at all. `MKGeneralException` is raised in hundreds of places.
   Nobody can tell which functions raise it, so nobody can tell what catching
   it means.

2. A shared type couples components that have nothing to do with each other.

   `except MKGeneralException` is written with one failure in mind: the one the
   author saw in the function they called. It also catches every other
   `MKGeneralException` raised anywhere below that call, by code the author
   has never read. Each new raise site widens every existing handler above it,
   and no diff will ever show that.

3. The types say nothing a handler could act upon.

   "The user can fix this" is not something the raising code can know. Whether
   a missing file is a user error, a bug or perfectly fine depends on the
   caller. A handler that receives `MKGeneralException` can print the message
   or give up. It cannot tell a syntax error in a configuration file from an
   unreachable host, so it cannot react to either.

4. The common base class does not deliver what it was introduced for.

   `MKException` was meant to make all of our exceptions catchable at once.
   `MKGeneralException`, by far the most common one, does not derive from it.
   The code base contains `except MKException, MKGeneralException`.

5. Some of these are control flow, not errors.

   `MKTerminate` means "stop the program". It is a jump to a handler that is
   assumed to exist at the top of the program. It derives from `Exception`,
   so every `except Exception` on the way up changes how the program
   terminates.

   `MKTerminate` and `MKTimeout` are also raised from signal handlers. Such an
   exception can surface between any two bytecode instructions: inside a
   `finally` block, while a lock is held, halfway through writing a file. No
   code can be reviewed for correctness against that.

6. All of this adds up to a protocol that nothing checks.

   The top level handlers of our programs only work if arbitrary code far
   below them raises the "right" type. No type checker, no test and no
   reviewer verifies that. Programs relying on it are correct by accident.


What to do instead
==================

* A failure the caller is expected to handle is a result. Return it: `X | None`,
  a union of small dataclasses, or `cmk.ccc.resulttype.Result`. The type
  checker then makes sure the caller deals with it.

* If an exception is the right tool, define a specific one in the package that
  raises it, next to the API it belongs to, and document it on the functions
  that raise it. Derive from `Exception` or from a fitting builtin, not from
  anything in this module. Catch it narrowly and close to the call.

* Translate at component boundaries: catch what your dependency documents and
  raise your own type (`raise ... from exc`) or return a result. The callers of
  your component should not have to know what it is built upon.

* Do not catch bugs. Let unexpected exceptions propagate to the crash
  reporting; that is what it is for.

* To end a program, return an exit code from `main()`. A signal handler records
  the signal and the main loop acts on it. It does not raise.

* Messages for the user are written at the boundary that knows the user: the
  command line interface, the GUI, the REST API. Library code reports what
  happened; it does not decide how to phrase it or whose fault it is.


Working with the existing code
==============================

Do not make it worse. If you change code that raises or catches one of these
exceptions, check whether that use can be replaced as part of your change.
Large mechanical migrations are not asked for: every site needs a decision
about what the failure means to its callers, and that takes someone who
understands the code in question.


Note to AI coding agents
========================

You will find these exceptions in a large part of the files you read. Do not
conclude that this is how errors are handled here. It is legacy. Do not add to
this module, do not subclass its exceptions, and do not reach for
`MKGeneralException` because the surrounding code does. Follow "What to do
instead". If a task seems to leave no other choice, tell the user so instead of
quietly extending the pattern.
"""

import enum
import signal
from typing import NoReturn

__all__ = [
    "MKIPAddressLookupError",
    "MKException",
    "MKGeneralException",
    "MKTerminate",
    "MKTimeout",
    "OnError",
]


class MKException(Exception):
    """Legacy, see the module docstring. Do not derive from this, do not catch it.

    Never raised directly. It was meant as a common base to make all of our
    exceptions catchable at once, which it is not: `MKGeneralException` does
    not derive from it. The exceptions below should move to the packages they
    actually belong to.
    """


class MKGeneralException(Exception):
    """An exception signaling the user can fix the underlying problem

    Important: This should not be used for errors that indicate actual bugs.

    Legacy, see the module docstring. Do not add new raise sites and do not
    derive from this. Whether the user can fix a problem is for the caller to
    decide. Raise a specific exception owned by your package, or return the
    failure.
    """


class MKTerminate(MKException):
    """Raised when the current program execution should be terminated.

    For example it is raised by the SIGINT signal handler to propagate the
    termination up the call stack. It is raised where the program termination
    is a "normal" case and neither a stack trace nor an error message should
    be printed. The program is stopped with exit code 0.

    Legacy, see the module docstring. Do not add new uses. This is control
    flow by exception, any `except Exception` on the way up swallows it, and a
    signal handler raising it interrupts code at arbitrary points. Record the
    signal and let the main loop return instead.
    """

    @classmethod
    def raise_from_signal(cls, _signum: object, _frame: object) -> NoReturn:
        raise cls


def raise_mkterminate_on_sigint() -> None:
    signal.signal(signal.SIGINT, MKTerminate.raise_from_signal)


class MKTimeout(MKException):
    """Raise when a timeout is reached.

    Note:
        It is used during keepalive mode. It is also used by the
        automations which have a timeout set.

    See also:
        `cmk.ccc.timeout` has a context manager using it.

    Legacy, see the module docstring. Do not add new uses. It is raised from
    a signal handler and therefore interrupts code at arbitrary points. Pass
    a timeout or a deadline to the operation that can block instead.
    """


class MKIPAddressLookupError(MKGeneralException):
    pass


class OnError(enum.Enum):
    RAISE = "raise"
    WARN = "warn"
    IGNORE = "ignore"
