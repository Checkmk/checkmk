#!/usr/bin/python

import math

def our_uptime():
    return int(float((file("/proc/uptime").read().split()[0])))

# replace simulator tags in output
def agent_simulator_process(output):
    try:
        while True:
            i = output.find('%{')
            if i == -1:
                break
            e = output.find('}', i)
            if e == -1:
                break
            simfunc = output[i+2 : e]
            replacement = str(eval("agentsim_" + simfunc))
            output = output[:i] + replacement + output[e+1:]
    except:
        pass

    return output

def agentsim_uptime(rate = 1.0, period = None): # period = sinus wave
    if period == None:
        return our_uptime() * rate
    else:
        a = (rate * period) / (2.0 * math.pi)
        u = our_uptime()
        return u * rate + int(a * math.sin(u / (2.0 * math.pi * period)))

def agentsim_enum(values, period = 1): # period is in seconds
    hit = our_uptime() / period % len(values)
    return values[hit]

