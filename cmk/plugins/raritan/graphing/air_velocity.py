from cmk.graphing.v1 import metrics, perfometers, Title

metric_raritan_air_velocity = metrics.Metric(
    name="raritan_air_velocity",
    title=Title("Air velocity"),
    unit=metrics.Unit(metrics.DecimalNotation("m/s"), metrics.AutoPrecision(3)),
    color=metrics.Color.ORANGE,
)

perfometer_raritan_air_velocity = perfometers.Perfometer(
    name="raritan_air_velocity",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(10)),
    segments=["raritan_air_velocity"],
)
