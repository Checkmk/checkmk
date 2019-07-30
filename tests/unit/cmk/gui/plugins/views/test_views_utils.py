import pytest

from cmk.gui.plugins.views.utils import (
    SorterEntry,
    _parse_url_sorters,
    _encode_sorter_url,
)


@pytest.mark.parametrize("url, sorters", [
    ('-svcoutput,svc_perf_val01,svc_metrics_hist', [('svcoutput', True), ('svc_perf_val01', False),
                                                    ('svc_metrics_hist', False)]),
    ('sitealias,perfometer~CPU utilization,site', [('sitealias', False),
                                                   ('perfometer', False, 'CPU utilization'),
                                                   ('site', False)]),
])
def test_url_sorters_parse_encode(url, sorters):
    sorters = [SorterEntry(*s) for s in sorters]
    assert _parse_url_sorters(url) == sorters
    assert _encode_sorter_url(sorters) == url
