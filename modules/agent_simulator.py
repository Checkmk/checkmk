#!/usr/bin/python

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

def agentsim_uptime(factor = 1.0):
    return our_uptime() * factor

def agentsim_enum(values, period = 1): # period is in seconds
    hit = our_uptime() / period % len(values)
    return values[hit]
