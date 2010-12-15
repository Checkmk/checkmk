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
