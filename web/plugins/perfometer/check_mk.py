# Perf-O-Meters for Check_MK's checks
#
# They are called with:
# 1. row -> a dictionary of the data row with at least the
#    keys "service_perf_data", "service_state" and "service_check_command"
# 2. The check command (might be extracted from the performance data
#    in a PNP-like manner, e.g if perfdata is "value=10.5;0;100.0;20;30 [check_disk]
# 3. The parsed performance data as a list of 7-tuples of
#    (varname, value, unit, warn, crit, min, max)


def perfometer_check_mk_df(row, check_command, perf_data):
    h = '<table><tr>'
    varname, value, unit, warn, crit, minn, maxx = perf_data[0]
    perc_used = 100 * (float(value) / float(maxx))
    perc_free = 100 - float(perc_used)
    color = { 0: "#0f8", 1: "#ff2", 2: "#f22", 3: "#fa2" }[row["service_state"]]
    h += '<td style="background-color: %s; width: %d%%;"></td>' % (color, perc_used)
    h += '<td style="background-color: white; width: %d%%;"></td>' % perc_free
    h += "</tr></table>"
# return "%d%% of %.1fGB used" % (perc_used, float(value)/1024.0), h
    return "%d%%" % perc_used, h
    return "%d%% used" % perc_used, h

perfometers["check_mk-df"] = perfometer_check_mk_df
perfometers["check_mk-vms_df"] = perfometer_check_mk_df
