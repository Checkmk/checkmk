"""Checker for incorrect string translation functions."""

import six

import astroid

from pylint.checkers import BaseChecker, utils
from pylint.interfaces import IAstroidChecker

BASE_ID = 78

def register(linter):
    """Register checkers."""
    linter.register_checker(TestChecker(linter))


class TestChecker(BaseChecker):
    """
    Checks for i18n translation functions (_, ugettext, ungettext, and many
    others) being called on something that isn't a string literal.

    Bad:
        _("hello {}".format(name))
        ugettext("Hello " + name)
        ugettext(value_from_database)

    OK:
        _("hello {}").format(name)

    The message id is `translation-of-non-string`.

    """

    __implements__ = (IAstroidChecker,)

    name = 'test-checker'

    TRANSLATION_FUNCTIONS = set([
        '_',
        'gettext',
        'ngettext', 'ngettext_lazy',
        'npgettext', 'npgettext_lazy',
        'pgettext', 'pgettext_lazy',
        'ugettext', 'ugettext_lazy', 'ugettext_noop',
        'ungettext', 'ungettext_lazy',
    ])

    MESSAGE_ID = 'test-jo'
    msgs = {
        'E%d10' % BASE_ID: (
            "LALAL %s()",
            MESSAGE_ID,
            "YO!",
        ),
    }

    @utils.check_messages(MESSAGE_ID)
    def visit_callfunc(self, node):
        """Called for every function call in the source code."""

        if not isinstance(node.func, astroid.Name):
            # It isn't a simple name, can't deduce what function it is.
            return

        if node.func.name not in self.TRANSLATION_FUNCTIONS:
            # Not a function we care about.
            return

        if not self.linter.is_message_enabled(self.MESSAGE_ID, line=node.fromlineno):
            return

        self.add_message(self.MESSAGE_ID, args=node.func.name, node=node)

        first = node.args[0]
        if isinstance(first, astroid.Const):
            if isinstance(first.value, six.string_types):
                # The first argument is a constant string! All is well!
                return

        # Bad!
        self.add_message(self.MESSAGE_ID, args=node.func.name, node=node)
