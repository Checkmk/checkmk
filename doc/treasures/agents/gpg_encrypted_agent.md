# Agent encryption with GNU PGP
Here is described how to use GPG to encrypt the agent output on the monitored host and decrypt it on the monitoring servers.

It is necessary to create a key with gpg and export the public key which is used for encryption. The public key must be available in the keyring of each monitored host.


## 1. Create a PGP key
The key needs to be created at the master monitoring server under the site user . First it needs to be validated that the tty could be accessed by gpg.

check with the command ls -la $(tty) that the site user owns the TTY. If not use chown to make the site user owner of the TTY:

```
# ll /dev/pts/0
crw------- 1 root tty 136, 0 Jul 23 15:04 /dev/pts/0
```
```
# chown site /dev/pts/0
```
```
# ll /dev/pts/0
crw------- 1 site tty 136, 0 Jul 23 15:05 /dev/pts/0
```

Then as site user create the key.

```
OMD[site]:~$ gpg  --full-gen-key
gpg (GnuPG) 2.1.18; Copyright (C) 2017 Free Software Foundation, Inc.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

Please select what kind of key you want:
   (1) RSA and RSA (default)
   (2) DSA and Elgamal
   (3) DSA (sign only)
   (4) RSA (sign only)
Your selection? 1
RSA keys may be between 1024 and 4096 bits long.
What keysize do you want? (3072) 2048
Requested keysize is 2048 bits
Please specify how long the key should be valid.
         0 = key does not expire
      <n>  = key expires in n days
      <n>w = key expires in n weeks
      <n>m = key expires in n months
      <n>y = key expires in n years
Key is valid for? (0) 0
Key does not expire at all
Is this correct? (y/N) y

GnuPG needs to construct a user ID to identify your key.

Real name: <realname> 
Email address: <mail@company.com> 
Comment: This key is to encrypt check_mk agent output on AIX hosts
You selected this USER-ID:
    "<realname> (This key is to encrypt check_mk agent output) <mail@company.com>"

Change (N)ame, (C)omment, (E)mail or (O)kay/(Q)uit? O
We need to generate a lot of random bytes. It is a good idea to perform
some other action (type on the keyboard, move the mouse, utilize the
disks) during the prime generation; this gives the random number
generator a better chance to gain enough entropy.
We need to generate a lot of random bytes. It is a good idea to perform
some other action (type on the keyboard, move the mouse, utilize the
disks) during the prime generation; this gives the random number
generator a better chance to gain enough entropy.
gpg: key 28544481AA963B75 marked as ultimately trusted
gpg: directory '/omd/sites/site/.gnupg/openpgp-revocs.d' created
gpg: revocation certificate stored as '/omd/sites/site/.gnupg/openpgp-revocs.d/99A7B744A37CA644D730803628544481AA963B75.rev'
public and secret key created and signed.

pub   rsa2048 2019-07-23 [SC]
      99A7B744A37CA644D730803628544481AA963B75
      99A7B744A37CA644D730803628544481AA963B75
uid                      <realname> (This key is to encrypt check_mk agent output ) <mail@company.com>
sub   rsa2048 2019-07-23 [E]
```
Check that the key is correct created:
```
MD[site]:~/bin$ gpg --list-keys
/omd/sites/site/.gnupg/pubring.kbx
------------------------------------
pub   rsa2048 2019-07-23 [SC]
      99A7B744A37CA644D730803628544481AA963B75
uid           [ultimate] <realname> (This key is to encrypt check_mk agent output) <mail@company.com>
sub   rsa2048 2019-07-23 [E]
```

Export the public key to a file.

```
gpg --armor --output key.public --export mail@company.com
```
## 1.1 Import key on client side
The public key must be imported under the same user as the agent script is running on every monitored host.
```
# gpg --import key.public
```
Validate that the key is there

```
# gpg --list-keys
/root/.gnupg/pubring.gpg
------------------------
pub   2048R/AA963B75 2019-07-23
uid                  <realname> (This key is to encrypt check_mk agent output) <mail@company.com>
sub   2048R/1A3EE9A0 2019-07-23
```


And change the trust level
```
# gpg --edit-key <realname> 
>trust
> 5
```



## 2. Agent Code
The code on the agent is basically just a wrapper around the original agent.

Create the following script:

/usr/bin/check_mk_agent_gpg:
```
#!/usr/bin/bash
/usr/bin/check_mk_agent | /usr/bin/gpg --batch -q --encrypt -r <realname> 
```
Create a inetd configuration. GPG encrypted Agent is listening on port 6559:
```
service check_mk_gpg
{
        type           = UNLISTED
        port           = 6559
        socket_type    = stream
        protocol       = tcp
        wait           = no
        user           = root
        server         = /usr/bin/check_mk_agent_gpg

        # listen on IPv4 AND IPv6 when available on this host
        #flags          = IPv6

        # If you use fully redundant monitoring and poll the client
        # from more then one monitoring servers in parallel you might
        # want to use the agent cache wrapper:
        #server         = /usr/bin/check_mk_caching_agent

        # configure the IP address(es) of your Nagios server here:
        #only_from      = 127.0.0.1

        # Don't be too verbose. Don't log every check. This might be
        # commented out for debugging. If this option is commented out
        # the default options will be used for this service.
        log_on_success =

        disable        = no
}
```
## 3. Server Code

~/local/share/check_mk/agents/special/agent_smith:
```
#!/bin/bash
echo "Special Agent Smith \n"
export GPG_TTY=$(tty)
/bin/nc $1 6559 < /dev/null | /usr/bin/gpg -q --batch --pinentry-mode loopback  --decrypt --passphrase-file <(echo 'password')
```
Create a rule “Individual program call instead of agent access” with following command line to execute:
```
~/local/share/check_mk/agents/special/agent_smith $HOSTADDRESS$
```
