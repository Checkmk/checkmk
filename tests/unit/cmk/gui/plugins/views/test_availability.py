import pytest

import cmk.render
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


@pytest.mark.parametrize("annotation_times,result", [
    ([
        (1543446000 + 7200, 1543446000 + 14400),
        (1543446000 + 28800, 1543446000 + 32400),
    ], cmk.render.time_of_day),
    ([
        (1543446000, 1543446000),
    ], cmk.render.time_of_day),
    ([(1543446000 - 3600, 1543446000 + 3600)], cmk.render.date_and_time),
    ([(1543446000, 1543446000 + 86400)], cmk.render.date_and_time),
    ([(1543446000 + 82800, 1543446000 + 172800)], cmk.render.date_and_time),
])
def test_get_annotation_date_render_function(annotation_times, result):
    annotations = [((None, None, None), {"from": s, "until": e}) for s, e in annotation_times]
    assert availability.get_annotation_date_render_function(
        annotations, {"range": ((1543446000, 1543446000 + 86399), "bla")}) == result
