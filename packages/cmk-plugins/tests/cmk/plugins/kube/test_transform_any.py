# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.kube.schemata import api
from cmk.plugins.kube.transform_any import parse_open_metric_samples


def test_parse_open_metric_samples_skips_unparsable_unrelated_metric() -> None:
    # An unrelated (non-volume) metric carrying a NUL byte in a label value must
    # not be JSON-parsed, otherwise it breaks parsing of the volume metrics we
    # actually care about.
    dump = (
        'some_unrelated_metric{label="bad\x00value"} 1.0\n'
        'kubelet_volume_stats_used_bytes{namespace="ns",persistentvolumeclaim="pvc"} 42.0\n'
    )

    samples = list(parse_open_metric_samples(dump))

    assert samples == [
        api.KubeletVolumeMetricSample(
            metric_name=api.KubeletVolumeMetricName.used,
            labels=api.KubeletVolumeLabels(namespace="ns", persistentvolumeclaim="pvc"),
            value=42.0,
        )
    ]
