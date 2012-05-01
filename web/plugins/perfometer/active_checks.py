
def perfometer_check_tcp(row, check_command, perfdata):
    time_ms = float(perfdata[0][1]) * 1000.0
    return "%.3f ms" % time_ms, \
        perfometer_logarithmic(time_ms, 1000, 10, "#20dd30")

perfometers["check-tcp"]           = perfometer_check_tcp
perfometers["check_tcp"]           = perfometer_check_tcp
perfometers["check_mk_active-tcp"] = perfometer_check_tcp

