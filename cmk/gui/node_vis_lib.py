from pathlib import Path
from typing import Optional, Any

from cmk.gui import watolib as watolib, config as config
from cmk.utils import store as store


class BILayoutManagement:
    _config_file = Path(watolib.multisite_dir()) / "bi_layouts.mk"

    @classmethod
    def save_layouts(cls) -> None:
        store.save_to_mk_file(str(BILayoutManagement._config_file),
                              "bi_layouts",
                              config.bi_layouts,
                              pprint_value=True)

    @classmethod
    def load_bi_template_layout(cls, template_id: Optional[str]) -> Any:
        return config.bi_layouts["templates"].get(template_id)

    @classmethod
    def load_bi_aggregation_layout(cls, aggregation_name: Optional[str]) -> Any:
        return config.bi_layouts["aggregations"].get(aggregation_name)

    @classmethod
    def get_all_bi_template_layouts(cls) -> Any:
        return config.bi_layouts["templates"]

    @classmethod
    def get_all_bi_aggregation_layouts(cls) -> Any:
        return config.bi_layouts["aggregations"]
