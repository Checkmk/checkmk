"""Managing the available automation calls"""

import abc
import six

import cmk
import cmk.utils.plugin_registry

import cmk.gui.config as config
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.watolib.activate_changes import ActivateChanges


class AutomationCommand(six.with_metaclass(abc.ABCMeta, object)):
    """Abstract base class for all automation commands"""
    @abc.abstractmethod
    def command_name(self):
        # type: () -> str
        raise NotImplementedError()

    @abc.abstractmethod
    def get_request(self):
        # type: () -> ...
        """Get request variables from environment

        In case an automation command needs to read variables from the HTTP request this has to be done
        in this method. The request produced by this function is 1:1 handed over to the execute() method."""
        raise NotImplementedError()

    @abc.abstractmethod
    def execute(self, request):
        # type: (...) -> ...
        raise NotImplementedError()

    def _verify_slave_site_config(self, site_id):
        # type: (str) -> None
        if not site_id:
            raise MKGeneralException(_("Missing variable siteid"))

        our_id = config.omd_site()

        if not config.is_single_local_site():
            raise MKGeneralException(
                _("Configuration error. You treat us as "
                  "a <b>remote</b>, but we have an own distributed WATO configuration!"))

        if our_id is not None and our_id != site_id:
            raise MKGeneralException(
                _("Site ID mismatch. Our ID is '%s', but you are saying we are '%s'.") %
                (our_id, site_id))

        # Make sure there are no local changes we would lose!
        changes = ActivateChanges()
        changes.load()
        pending = list(reversed(changes.grouped_changes()))
        if pending:
            message = _("There are %d pending changes that would get lost. The most recent are: "
                       ) % len(pending)
            message += ", ".join(change["text"] for _change_id, change in pending[:10])

            raise MKGeneralException(message)


class AutomationCommandRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return AutomationCommand

    def plugin_name(self, plugin_class):
        return plugin_class().command_name()


automation_command_registry = AutomationCommandRegistry()


@automation_command_registry.register
class AutomationPing(AutomationCommand):
    def command_name(self):
        return "ping"

    def get_request(self):
        return None

    def execute(self, _unused_request):
        return {
            "version": cmk.__version__,
            "edition": cmk.edition_short(),
        }
