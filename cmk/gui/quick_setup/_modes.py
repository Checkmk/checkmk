from typing import Sequence

from cmk.gui.i18n import _
from cmk.gui.type_defs import Icon
from cmk.gui.wato._main_module_topics import MainModuleTopicQuickSetup
from cmk.gui.watolib.main_menu import MainModuleRegistry, ABCMainModule, MainModuleTopic


def register(main_module_registry: MainModuleRegistry) -> None:
    pass


class MainModuleQuickSetupAWS(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "quick_setup_aws"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicQuickSetup

    @property
    def title(self) -> str:
        return _("Amazon Web Service (AWS)")

    @property
    def icon(self) -> Icon:
        return "quick_setup_aws"

    @property
    def permission(self) -> None | str:
        return None

    @property
    def description(self) -> str:
        return _("Configure Amazon Web Service (AWS) monitoring in Checkmk")

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False

    @classmethod
    def megamenu_search_terms(cls) -> Sequence[str]:
        return ["aws"]
