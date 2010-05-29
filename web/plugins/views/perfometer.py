# Painters for Perf-O-Meter

perfometers = {}

perfometer_plugins_dir = defaults.web_dir + "/plugins/perfometer"
for fn in os.listdir(perfometer_plugins_dir):
    if fn.endswith(".py"):
	execfile(perfometer_plugins_dir + "/" + fn)


def paint_perfometer(row):
    perfstring = str(row["service_perf_data"].strip())
    if not perfstring:
        return "", ""

    parts = perfstring.split()
    # Try if check command is appended to performance data
    # in a PNP like style
    if parts[-1].startswith("[") and parts[-1].endswith("]"):
        check_command = parts[-1][1:-1]
        del parts[-1]
    else:
        check_command = row["service_check_command"]

    # Find matching perf-o-meter function
    perf_painter = perfometers.get(check_command)
    if not perf_painter:
        return "", ""

    # Parse performance data, at least try
    try:
        perf_data = []
        for part in parts:
            varname, values = part.split("=")
            value_parts = values.split(";")
            while len(value_parts) < 5:
                value_parts.append(None)
            value, warn, crit, min, max = value_parts[0:5]
            # separate value from unit
            i = 0
            while i < len(value) and (str.isdigit(value[i]) or value[i] in ['.', ',', '-']):
                i += 1
            unit = value[i:]
            value = value[:i]
            perf_data.append((varname, value, unit, warn, crit, min, max))
    except:
        perf_data = None

    try:
        title, h = perf_painter(row, check_command, perf_data)
# return "perfometer", '<div class=title>%s</div>' % (title + h)
        return "perfometer", '<a href="%s"><div class=title>%s</div>%s</a>' % (pnp_url(row), title, h)
    except Exception, e:
        if config.debug:
            raise
        return "perfometer", ("invalid data: %s" % e)

multisite_painters["perfometer"] = {
    "title" : "Service Perf-O-Meter",
    "short" : "Perf-O-Meter",
    "columns" : [ "service_perf_data", "service_state", "service_check_command" ],
    "paint" : paint_perfometer
}
