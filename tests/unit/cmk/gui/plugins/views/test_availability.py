import pytest

import cmk.gui.plugins.views.availability as availability


@pytest.mark.parametrize("annotation_from,annotation_until,result", [
    (40, 50, True),
    (10, 70, True),
    (10, 30, True),
    (10, 40, True),
    (40, 60, True),
    (40, 70, True),
    (10, 20, False),
    (61, 70, False),
])
def test_relevant_annotation_times(annotation_from, annotation_until, result):
    assert availability._annotation_affects_time_range(annotation_from, annotation_until, 30,
                                                       60) == result
