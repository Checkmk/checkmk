# Bandit `# nosec` Exclusions

The following table contains the reasoning behind Bandit exclusions in our source code.
All exclusions should be marked using `# nosec <rule id> # <bns id>` in the code.
Note that Bandit is picky about the exact format.

| Bandit nosec ID | Bandit Rule | Exclusion Reason |
| --- | --- | --- |
| `BNS:9a7128` | `B301` | `ObjectStore` has a pickle serializer which it uses to store and load files from disk. To mitigate the risks, it makes sure that only non-world-writable files are loaded. |
