#!/usr/bin/python
# Put this file into share/check_mk/web/plugins/perfometer

def perfometer_modbus_value(row, check_command, perf_data):
    value = int(perf_data[0][1])
    return perf_data[0][1], perfometer_logarithmic(value, value*3, 2, '#3366cc')

perfometers['check_mk-modbus_value'] = perfometer_modbus_value


