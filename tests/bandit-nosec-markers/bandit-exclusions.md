# Bandit `# nosec` Exclusions

The following table contains the reasoning behind Bandit exclusions in our source code.
All exclusions should be marked using `# nosec <rule id> # <bns id>` in the code.
Note that Bandit is picky about the exact format.

| Bandit nosec ID | Bandit Rule | Exclusion Reason |
| --- | --- | --- |
| `BNS:c3c5e9` | `B301` | `PackedConfigStore` loads a config from file via `pickle.load`. The path is hard-coded to `cmk.utils.paths.core_helper_config_dir` in `ConfigPath`, which is only writable by the site user. |
| `BNS:9a7128` | `B301` | `ObjectStore` has a pickle serializer which it uses to store and load files from disk. To mitigate the risks, it makes sure that only non-world-writable files are loaded. |
| `BNS:28af27` | `B310` | The URL or the scheme is hardcoded, so the scheme cannot change. |
| `BNS:6b61d9` | `B310` | The URL is explicitly validated. |
| `BNS:97f639` | `B321`, `B402` | The checked service requires FTP. |
| `BNS:67522a` | `B602`, `B605` | External inputs to the command have been quoted for shell-safety. |
| `BNS:2b5952` | `B602` | Intended Shell functionaility, should be reviewed for mitigating security layers in the future |
| `BNS:f6c1b9` | `B605` | Shell command has been reviewed. |
| `BNS:537c43` | `B104` | Comparison against "0.0.0.0", if true then the address is set to "127.0.0.1" |
| `BNS:bbfc92` | `B701` | The test code in the examples is hard coded and does not currently take in external input. |
| `BNS:016141` | `B501` | certificate validation not performed as it may break existing deployments of clients. |
| `BNS:e9bfaa` | `B303` | Only used to display fingerprints and in testing. |
