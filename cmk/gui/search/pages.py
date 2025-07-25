from typing import cast, get_args, override

from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.pages import AjaxPage, PageResult

from .engines.monitoring import MonitoringSearchEngine
from .engines.setup import SetupSearchEngine
from .type_defs import Provider
from .unified import UnifiedSearch


class PageUnifiedSearch(AjaxPage):
    @override
    def page(self, config: Config) -> PageResult:
        query = request.get_str_input_mandatory("q")
        provider = self._parse_provider_query_param()

        setup_engine = SetupSearchEngine()
        monitoring_engine = MonitoringSearchEngine()
        unified_search_engine = UnifiedSearch(setup_engine, monitoring_engine)

        response = unified_search_engine.search(query, provider, config)

        return {
            "url": request.url,
            "query": query,
            "counts": response.counts.serialize(),
            "results": [result.serialize() for result in response.results],
        }

    def _parse_provider_query_param(self) -> Provider | None:
        if (provider := request.get_str_input("provider")) is None:
            return None

        return cast(Provider, provider) if provider in get_args(Provider) else None
