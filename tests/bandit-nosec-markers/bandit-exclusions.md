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
| `BNS:9a7128` | `B301` | `ObjectStore` has a pickle serializer which it uses to store and load files from disk. To mitigate the risks, it makes sure that only non-world-writable files are loaded. |
| `BNS:c3c5e9` | `B301` | `PackedConfigStore` loads a config from file via `pickle.load`. The path is hard-coded to `cmk.utils.config_path.VersionedConfigPath.ROOT`, which is only writable by the site user. |
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
| `BNS:13b2c8` | `B108` | Using /tmp directory on host, reviewed. |
| `BNS:248184` | `B602` | The hardcoded find command used here outputs the modification time (as a number), assuming the input is strictly a path. |
| `BNS:b00359` | `B602` | Intended Shell functionality.|
| `BNS:ff2c84` | `B411` | The xmlrpc submodule version being used is safe to xml attacks. |
| `BNS:f159c1` | `B507` | The AutoAdd policy is used, which is the human default. Also the host keys are persisted |
| `BNS:fa3c6c` | `B608` | The inputs to the SQL expression are controlled by the script, not by the user. |
| `BNS:6b6392` | `B608` | The inputs have been parameterized and controlled. |
| `BNS:666c0d` | `B608` | This case is not truly an SQL injection; it is a command injection that is already being addressed. |
| `BNS:d840de` | `B608` | Removing backticks from user input make sure the input can't escape from enclosing backtick. Bigquery treat `{tableid}` as an identifier rather than part of SQL syntax. |
| `BNS:ccacbd` | `B302` | The data loaded by marshal.loads() is being parsed with a well-typed class and is not fed to any dangerous function. |
| `BNS:4607da` | `B302` | Intended usage of marshal.loads(). |
| `BNS:f60b87` | `B608` | False positive hardcoded SQL. |
| `BNS:6f5399` | `B202` | False positive, it's a zipfile not tarfile. |
