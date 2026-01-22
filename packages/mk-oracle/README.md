# Oracle SQL check

## Oracle instant client download and installation

### Linux

Please, download and unzip Oracle Instant Client _zipped_ installation for your Linux.
Find it on Oracle’s download page:
https://www.oracle.com/ch-de/database/technologies/instant-client/downloads.html

We recommend to use version 21.

For unzipping, use command like this:
assuming that you are using `instantclient-basiclite-linux.x64-21.20.0.0.0dbru.zip`
Choose one of the following options:

1. Global Installation

```
    sudo unzip -j instantclient-basiclite-linux.x64-21.19.0.0.0dbru.zip -d /opt/checkmk/oracle-instant-client
```

2. In Agent installation(recommended)

```
    sudo unzip -j instantclient-basiclite-linux.x64-21.19.0.0.0dbru.zip -d /path/to/agent/plugins/packages/mk-oracle
```

For default _legacy deployment_ plugins path for Checkmk agent on Linux is `/usr/lib/check_mk_agent/plugins/`

```
sudo unzip -j /home/$USER/Downloads/instantclient-basic-linux.x64-21.20.0.0.0dbru.zip -d /usr/lib/check_mk_agent/plugins/packages/mk-oracle/
```

For default _single directory deployment_ plugins path for Checkmk agent on Linux is `/opt/checkmk/agent/default/package/plugins`

```
sudo unzip -j /home/$USER/Downloads/instantclient-basic-linux.x64-21.20.0.0.0dbru.zip -d /opt/checkmk/agent/default/package/plugins/packages/mk-oracle/
```

you may determine the path to the agent installation by running command:

```
sudo check_mk_agent | grep "^pluginsdir " | head -1
```

Please install oracle instant client to be write-accessible only by admin user.

After the Instant Client libraries are installed you may use WATO to configure type of deployment

_Ubuntu Linux_ may require linking libaio

```
ln -sf "/lib/x86_64-linux-gnu/libaio.so.1t64" "/lib/x86_64-linux-gnu/libaio.so.1"
```

### Windows

Download and unzip Oracle Windows installation guide to configure your Oracle Instant Client in folder of your choice.
Find it on Oracle’s download page:
https://www.oracle.com/ch-de/database/technologies/instant-client/downloads.html

Choose one of the following options:

1. Global Installation
   PATH must contain the path to the folder where dlls are stored.
   For example: `C:\oracle\instantclient_21_3`
2. In Agent Installation(recommended)
   you unzip \*.dll files to `PROGRAMDATA%/checkmk/agent/plugins/packages/mk-oracle` folder.

## Oracle Wallet Authentication

Oracle Wallet provides a secure way to authenticate to Oracle databases without storing passwords in plain text configuration files.
The plugin supports Oracle Wallet authentication with the following behavior:

### Default Configuration

- **TNS_ADMIN**: By default, the `TNS_ADMIN` environment variable is set to `MK_CONFDIR` (typically `/etc/check_mk` on Linux).
- **Wallet Location**: The default wallet location is `MK_CONFDIR/oracle_wallet` (e.g., `/etc/check_mk/oracle_wallet`).

### Enabling Wallet Authentication

To enable Oracle Wallet authentication, set the authentication type to `wallet` in your YAML configuration file:

```yaml
oracle:
  main:
    connection:
      hostname: 127.0.0.1
      port: 1521
      service_name: FREE
    authentication:
      type: wallet # auth type is set to wallet
```

### Workflow 1: Using Default Configuration (No explicit tns_admin)

When the authentication type is set to `wallet` and no `tns_admin` is explicitly configured:

1. The plugin sets `TNS_ADMIN` to `MK_CONFDIR`.
2. A `sqlnet.ora` file is created in `MK_CONFDIR` (if it doesn't already exist) with the wallet location pointing to `MK_CONFDIR/oracle_wallet`.
3. You need to place your Oracle Wallet files in `MK_CONFDIR/oracle_wallet`.

**Note:** You can also pre-create `sqlnet.ora`, `tnsnames.ora`, and the `oracle_wallet` directory with wallet files in `MK_CONFDIR` before running the plugin.

#### Creating the Oracle Wallet

Assuming `MK_CONFDIR` is `/etc/check_mk` and this is your config file:

```yaml
oracle:
  main:
    connection:
      hostname: 127.0.0.1
      port: 1521
      service_name: FREE
    authentication:
      type: wallet
```

Use the following commands to create and configure the wallet:

1. Create the wallet directory and initialize it:

```bash
mkstore -wrl /etc/check_mk/oracle_wallet -create
```

2. Add credentials to the wallet (replace with your actual connection details):

```bash
mkstore -wrl /etc/check_mk/oracle_wallet -createCredential 127.0.0.1:1521/FREE/FREE checkmk myPassword
```

#### Example sqlnet.ora File

```
LOG_DIRECTORY_CLIENT = /var/log/check_mk/oracle_client
DIAG_ADR_ENABLED = OFF

SQLNET.WALLET_OVERRIDE = TRUE
WALLET_LOCATION =
 (SOURCE=
   (METHOD = FILE)
   (METHOD_DATA = (DIRECTORY=/etc/check_mk/oracle_wallet))
 )
```

### Workflow 2: Using Custom tns_admin Location

When the authentication type is set to `wallet` and `tns_admin` is explicitly set in the configuration:

```yaml
oracle:
  main:
    connection:
      hostname: 127.0.0.1
      port: 1521
      tns_admin: /custom/path/to/tns_admin
    authentication:
      type: wallet
```

In this case:

1. The plugin sets `TNS_ADMIN` to the value specified in `tns_admin`.
2. The plugin does **not** create any configuration files automatically.
3. You are responsible for managing all configuration files in your custom `TNS_ADMIN` directory, including:
   - `sqlnet.ora` (with wallet location configuration)
   - `tnsnames.ora` (if using TNS aliases)
   - Oracle Wallet files in the location specified in your `sqlnet.ora`

This workflow is useful when you have an existing Oracle configuration setup that you want to reuse.
