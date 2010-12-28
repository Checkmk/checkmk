Darstellung der Aggregation

Datenbank(H, N) [worst]:
    Logfiles(H, N),
    Tablespaces(H, N),
    HostRessources(H)

HostRessources(H) [worst]:
    service H Kernel|Memory
    service H CPU
    Networking(H,*)

Networking(H,NIC) [worst]:
    service H NIC <NIC> .*

Logfiles(H, N) [worst(2)]:
    service H LOG /var/log/oracle/N.log

Warehouse(H1,H2,DB):
    ClusterHostRessources(H1,H2)
    Datenbank(H1,DB)
    Datenbank(H2,DB)

ClusterHostRessources(H1,H2) [best]:
    HostRessources(H1)
    HostRessources(H2)

aggregate DBs Datenbank('zsap51u', 'DKV')
aggregate DBs Datenbank('zsap52u', 'DKP')
aggregate HostRessources(*)

aggregation_rules["DB"] =  (
 "Datenbank $N$", [ 'H', 'N' ], 'worst', [
      ( "Logfiles",       [ 'H', 'N' ] ),
      ( "TableSpaces",    [ 'H', 'N' ] ),
      ( "HostRessources", [ 'H' ] ),
  ]
)

aggregation_rules["Networking"] = ( 
  "Networking", "NIC $NIC$", [ 'H', 'NIC' ], 'worst(2)', [ 
      ('$H$', 'NIC $NIC$ .*',) 
  ]
)

aggregations = [
  ( "DBs",   "DB",         [ 'zsap51u', 'DKV' ] ),
  ( "DBs",   "DB",         [ 'zsap.*',  'D??' ] ),
  ( "Hosts", "Networking", [ '.*' ] ),
]


==> Das ganze muss vorkompiliert werden, da es vermutlich zur Laufzeit viel
zu langsam ist. Am Ende wird daraus eine Baumstruktur, die in einer Python-
Datei gespeichert wird.

So arbeitet der Aggregationskompiler:

Zunächst holen wir *alle* hosts und services, von allen sites
g_services['zbghora50'] = ( ['linux', 'prod', test'], [ "NIC eth0 counters", "NIC eth1", ... ] )

aggregation_forest = {}
for group, rulename, args in aggregations:
    # Schwierigkeit hier: die args können reguläre Ausdrücke enthalten.
    rule = aggregation_rules[rulename]
    entries = aggregation_forest.get(group, [])
    group += compile_aggregation(rule, args)
    aggregation_forest[group] = entries


def compile_aggregation(rule, args):
    description, arglist, func, nodes = rule
    arg = dict(zip(arglist, args))
    # Die Argumente enthalten reguläre Ausdrücke. Wir müssen jetzt alle Inkarnationen
    # finden
    found = []
    for node in nodes:
        found += aggregate_node(arg, node)
    

def aggregate_node(arg, node):
    if type(node[1]) == str: # leaf node
        return aggregate_leaf_node(arg, node[0], node[1])
    else
        return aggregate_inter_node(arg, node[0], node[1])

def aggregate_leaf_node(arg, host, service):
    # replace placeholders in host and service with arg
    # service = 'NIC $NIC .*'
    host_re = instantiate(host, arg)
    # service = 'NIC $NIC .*'
    service_re = instantiate(service, arg)
    # service_re = (['NIC'], 'NIC (.*) .*')  # Liste von argumenten

    found = {}
    for host, (tags, services) in g_services.items():
        # Tags vom Host prüfen (hier noch nicht in Konfiguration enthalten)
        instargs, inst_host = do_match(host_re, host)
        if instargs:
            newarg = arg.copy()
            newarg.update(instargs) # Argumente sind jetzt instanziiert
            instargs, inst_svc = do_match(service_re, service)
            if instargs:
                newarg = arg.copy()
                newarg.update(instargs) # Argumente sind jetzt instanziiert und enthalten eine RE mehr
                entries = found.get(newarg, [])
                entries.append((inst_host, inst_svc))
                found[newarg] = entries

    # Jetzt in eine Liste umwandeln
    return in_liste(found)

def aggregate_inter_node(arg, ...):
     # fehlt

=> Am Ende kommt eine Reihe von Bäumen ohne irgendwelche Platzhalter
raus. Jetzt bräuchte man dafür noch möglich optimierte Livestatus-anfragen.
Dabei reicht es wohl, wenn man auf die für eine Aggregation notwendigen
Hosts filtert. Diese sollte beim Baum jeweils mitgespeichert sein.
So kann man auch - wenn eine Aggregation nur einen einzigen Host braucht - 
diese dem Host direkt zuordnen.
    
    








