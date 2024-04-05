# Bandit `# nosec` Exclusions

The following table contains the reasoning behind Bandit exclusions in our source code.
All exclusions should be marked using `# nosec <rule id> # <bns id>` in the code.
Note that Bandit is picky about the exact format.

| Bandit nosec ID | Bandit Rule | Exclusion Reason |
| --- | --- | --- |
| `BNS:aee528` | `B102` | Config file data would be in an expected format however alternatives handle process threads different which may impact timings or cause hanging when loading configurations. |
| `BNS:a29406` | `B102` | User defined input expected within executed files such as custom entries within agent plugin .cfg files. |
| `BNS:c29b0e` | `B103` | A python file is compiled and marked as executable. |
| `BNS:ce45cd` | `B103` | Creates a spoolfile, this is probably ought to be deleted by the other process. |
| `BNS:7e6b08` | `B103` | We set the traverse permission on a folder, since there are files which needs to be world accessible.|
| `BNS:537c43` | `B104` | Comparison against "0.0.0.0", if true then the address is set to "127.0.0.1". |
| `BNS:7a2427` | `B108` | False positive, the temp file/directory is located inside a safe directory. |
| `BNS:773085` | `B113` | Timeout policy to be reviewed. |
| `BNS:9a7128` | `B301` | `ObjectStore` has a pickle serializer which it uses to store and load files from disk. To mitigate the risks, it makes sure that only non-world-writable files are loaded. |
| `BNS:c3c5e9` | `B301` | `PackedConfigStore` loads a config from file via `pickle.load`. The path is hard-coded to `cmk.utils.paths.core_helper_config_dir` in `ConfigPath`, which is only writable by the site user. |
| `BNS:e9bfaa` | `B303` | Only used to display fingerprints and in testing. |
| `BNS:02774b` | `B303` | SHA1 is still used by the agent bakery and mkbackup for compatibility reasons. Switching is planned. |
| `BNS:6b61d9` | `B310` | The URL is explicitly validated. |
| `BNS:28af27` | `B310` | The URL or the scheme is hardcoded, so the scheme cannot change. |
| `BNS:97f639` | `B321`, `B402` | The checked service requires FTP. |
| `BNS:501305` | `B323` | Intended behaviour and configurable via option. |
| `BNS:eb967b` | `B324` | SHA1 HMAC is fine and is the preferred standard for TOTP, bandit only sees the use of SHA1. |
| `BNS:016141` | `B501` | Certificate validation not performed as it may break existing deployments of clients. |
| `BNS:2aa916` | `B601` | `nas_db_env` is sanitized with shlex.quote. |
| `BNS:67522a` | `B602`, `B605` | External inputs to the command have been quoted for shell-safety. |
| `BNS:2b5952` | `B602`, `B605` | Intended Shell functionaility, should be reviewed for mitigating security layers in the future. |
| `BNS:f6c1b9` | `B605` | Shell command has been reviewed. |
| `BNS:bbfc92` | `B701` | The test code in the examples is hard coded and does not currently take in external input. |
| `BNS:a7d6b8` | `B202` | Bandit is not updated (tarfile check added July 2022) for the changes to tarfile.extractall() filters from python 3.12. |
