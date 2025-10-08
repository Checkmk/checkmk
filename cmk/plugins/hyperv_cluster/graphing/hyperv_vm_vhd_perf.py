from cmk.graphing.v1 import perfometers, Title
from cmk.graphing.v1.metrics import (
    Color,
    DecimalNotation,
    Metric,
    StrictPrecision,
    Unit,
)

PERCENT_UNIT = Unit(DecimalNotation("%"), StrictPrecision(2))

prefix = "hyperv_vhd_metrics_"


metric_hyperv_vhd_file_size_percent = Metric(
    name=f"{prefix}file_size_percent",
    title=Title("Current disk size %"),
    unit=PERCENT_UNIT,
    color=Color.PURPLE,
)

perfometer_hyperv_vhd_file_size_percent = perfometers.Perfometer(
    name=f"{prefix}file_size_percent_perf",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
    segments=[f"{prefix}file_size_percent"],
)
