import cmk.gui.plugins.metrics.rrd_fetch as rf


def test_needed_elements_of_expression():
    assert set(
        rf.needed_elements_of_expression(('transformation', ('q90percentile', 95.0), [
            ('rrd', u'heute', u'CPU utilization', 'util', 'max')
        ]))) == {('heute', 'CPU utilization', 'util', 'max')}
