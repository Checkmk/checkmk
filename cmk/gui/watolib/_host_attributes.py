from typing import Optional

from cmk.gui.config import active_config, register_post_config_load_hook
from cmk.gui.watolib.host_attributes import (
    _clear_config_based_host_attributes,
    _declare_host_tag_attributes,
    declare_custom_host_attrs,
    transform_pre_16_host_topics,
)
from cmk.gui.watolib.hosts_and_folders import Folder

_update_config_based_host_attributes_config_hash: Optional[str] = None


def _update_config_based_host_attributes() -> None:
    global _update_config_based_host_attributes_config_hash

    def _compute_config_hash() -> str:
        return str(hash(repr(active_config.tags.get_dict_format()))) + repr(
            active_config.wato_host_attrs
        )

    # The topic conversion needs to take place before the _compute_config_hash runs
    # The actual generated topics may be pre-1.5 converted topics
    # e.g. "Custom attributes" -> "custom_attributes"
    # If we do not convert the topics here, the config_hash comparison will always fail
    transform_pre_16_host_topics(active_config.wato_host_attrs)

    if _update_config_based_host_attributes_config_hash == _compute_config_hash():
        return  # No re-register needed :-)

    _clear_config_based_host_attributes()
    _declare_host_tag_attributes()
    declare_custom_host_attrs()

    Folder.invalidate_caches()

    _update_config_based_host_attributes_config_hash = _compute_config_hash()


def register():
    # Make the config module initialize the host attributes after loading the config
    register_post_config_load_hook(_update_config_based_host_attributes)
