#!/usr/bin/env python


"""
Password store

this can be run as an executable or imported as a module

How it works (user view):

* This stores arbitrary secrets and manages access to those secrets
* To read a secret a user has to have created the secret himself (making him the owner) or
  been given read-access by the owner
* for this to work, a user has to have an account inside the password store. Anyone with write
  access to the store file can create accounts and store secrets.
* A secret can only be read by an account that has been given access (ensured through encryption)
* A secret can only be shared, changed or removed by an account that has created it. This however
  is only ensured by the api, since anyone who can write to the store can overwrite/damage it
  anyway.
* Anyone with access to the private key of a user can control that user (provided he knows the
  password if one was set)
* One can have multiple private keys

How it works (technical view):

* the store file contains a list of all store-accounts (user name and base64 encoded public key) ...
* each secret is stored with its owner (name) and the secret encrypted (and base64 encoded)
  with the public key of each reader (owner + all users with whom the secret was shared).
* when trying to read a secret, the caller needs to specify user user name and the store will try
  to find the private key for that user to decrypt the data.
* The private key may be password protected to add a level of security if the private key file is
  accessible by unauthorized users, but this requires the caller to provide a way to make
  passwords available (see password callback)
* The password store supports concurrent access from different processes. It is however not itself
  thread-safe.
  Concurrency is achieved like this:
      a) When the password file is updated, this happens in an atomic rename operation. This
         way reading the password file always produces a consistent state
      b) the instance contains a cache of the password file. All read operation thereby access a
         consistent state which may not be current. The cache may be manully updated using a call
         to "sync()"
      c) During change operations the file is locked on the fs level. Immediately after locking the
         file the current state is re-read. This ensures two processes don't overwrite each others
         changes.
  Important: The cache for read-operations is also updated during a save. This means that if you
    "read - write - read" or "read - sync - read", the state between those two reads may not be
    consistent!

File layout (json):
    {
    "keydata": {
        "user1": "<pem encoded public key>",
        "user2": "<pem encoded public key>"
        ...
    }
    "secrets": {
        "key1": {
            "owner": "user1",
            "data": {
                "user1": "<rsa encrypted (with public key of user1) and base64 encoded secret>",
                "user2": "<rsa encrypted (with public key of user2) and base64 encoded secret>",
                ...
            }
        },
        "keyn": {
            "owner": "usern",
            "data": {
                "user2": "<rsa encrypted (with public key of user2) and base64 encoded secret>",
                ...
                "usern": "<rsa encrypted (with public key of usern) and base64 encoded secret>"
            }
        }
    }

"""


from argparse import ArgumentParser
from tempfile import mkdtemp
from base64 import b64decode, b64encode
from tempfile import NamedTemporaryFile
import json
import errno
import sys
import os
import stat
import logging
import shutil
import fcntl


class UnknownUserException(Exception):
    def __init__(self, user):
        super(UnknownUserException, self).__init__("No such user \"%s\"" % user)


class UserExistsException(Exception):
    def __init__(self, user):
        super(UserExistsException, self).__init__("User \"%s\" exists" % user)


class InvalidKeyException(Exception):
    def __init__(self, key):
        super(InvalidKeyException, self).__init__("No such key \"%s\"" % key)


class NotAuthorizedException(Exception):
    def __init__(self, key, user, action="access"):
        super(NotAuthorizedException, self).__init__("\"%s\" is not authorized to %s \"%s\"" %\
                                                     (user, action, key))


class KeyMissingException(Exception):
    def __init__(self, user):
        super(KeyMissingException, self).__init__("Key for user \"%s\" missing" % user)


class DecryptException(Exception):
    def __init__(self, inner):
        super(DecryptException, self).__init__("Decryption failed, wrong password? (%s)" % str(inner))

"""
class GPGBackend(object):
    ""
    NOT FUNCTIONAL

    This was a promising attempt to use gpg as the backend with would allow us to use
    the robust gpg infrastructure including keyring.
    Unfortunately generating keys from code fails with a non-descript error and on the console
    it can take forever
    ""

    from pyme import core, constants
    from pyme.errors import GPGMEError

    def __init__(self, key_dir=None):
        self.__context = self.core.Context()
        if not self.core.engine_check_version(self.constants.PROTOCOL_OpenPGP):
            raise RuntimeError("GPG not installed/wrong version")

        self.__temporary_keydir = key_dir is None

        if key_dir is None:
            key_dir = mkdtemp()
            key_path = os.path.join(key_dir, "pubring.gpg")
            with open(key_path, "w") as f:
                if key_data is not None:
                    f.write(key_data)
            os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)

        self.__context.set_engine_info(constants.PROTOCOL_OpenPGP, None, key_dir)
        self.__key_dir = key_dir

        self.__context.set_passphrase_cb(self.__password_callback)
        self.__context.set_armor(1)

    def cleanup(self):
        if self.__temporary_keydir:
            shutil.rmtree(self.__key_dir)

    def __password_callback(self, hint, desc, prev_bad):
        return "password"

    def set_key_data(self, key_data):
        key_path = os.path.join(self.__key_dir, "pubring.gpg")
        with open(key_path, "w") as f:
            if key_data is not None:
                f.write(key_data)

    def key_data(self):
        with open(os.path.join(self.__key_dir, "pubring.gpg"), "r") as f:
            return f.read()

    def add_user(self, user, passphrase):
        self.__context.op_genkey("<GnupgKeyParms format=\"internal\">"
                                 "Key-Type: RSA"
                                 "Key-Length: 1024"
                                 "Expire-Date: 0"
                                 "Name-Real: %s"
                                 "Passphrase: %s"
                                 "</GnupgKeyParms>" % (user, passphrase), None, None)

    def encrypt(self, data, readers):
        plain = self.core.Data(data)
        encrypted = {}
        for reader_name in readers:
            cipher = self.core.Data()
            self.__context.op_keylist_start(reader_name, 0)
            r = self.__context.op_keylist_next()
            try:
                self.__context.op_encrypt([r], 1, plain, cipher)
            except GPGMEError, e:
                raise UnknownUserException(reader_name)

            cipher.seek(0, 0)
            encrypted[reader] = cipher.read()
        return encrypted

    def decrypt(self, data, reader):
        plain = self.core.Data()
        cipher = self.core.Data(str(data))
        self.__context.op_decrypt(cipher, plain)
        plain.seek(0, 0)
        return plain.read()
"""

class CryptoBackend(object):
    """
    a custom backend using the Crypto library
    """

    from Crypto import Random
    from Crypto.Cipher import AES
    from Crypto.PublicKey import RSA

    def __init__(self, private_key_dir, password_cb):
        self.__private_key_dir = private_key_dir
        self.__public_keys = {}
        self.__password_callback = password_cb

    def cleanup(self):
        """
        no temporary data to clean up
        """
        pass

    def set_key_data(self, key_data):
        """
        update key data
        """
        self.__public_keys = dict((user, self.RSA.importKey(key))
                                  for user, key in key_data.items())

    def key_data(self):
        """
        retrieve key data
        """
        return dict((user, key.exportKey("PEM"))
                    for user, key in self.__public_keys.items())

    def all_users(self):
        return self.__public_keys.keys()

    def add_user(self, user, passphrase):
        """
        add a new user
        @param user: username
        @param passphrase: password for encrypting the private key file. May be None

        this will throw an UserExistsException if the user already exists
        """

        if user in self.__public_keys:
            raise UserExistsException(user)

        # generate random private key
        random_generator = self.Random.new().read
        key = self.RSA.generate(2048, random_generator)
        # store the encrypted private key
        key_path = os.path.join(self.__private_key_dir, user + ".pem")
        with open(key_path, "w") as f:
            f.write(key.exportKey("PEM", passphrase))
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
        # store the public key in the keyfile
        self.__public_keys[user] = key.publickey()

    def encrypt(self, data, readers):
        """
        return a dictionary with the data encrypted for each reader with their
        public key
        """
        encrypted = {}
        for reader_name in readers:
            if not reader_name in self.__public_keys:
                raise UnknownUserException(reader_name)
            encrypted[reader_name] = b64encode(self.__public_keys[reader_name].encrypt(data, 0)[0])
        return encrypted

    def decrypt(self, data, reader):
        """
        return the data decrypted with the private key of reader. The
        password callback is used to look up the passphrase used to encrypt the key
        """
        pw = self.__password_callback(reader)
        key_path = os.path.join(self.__private_key_dir, reader + ".pem")
        if not os.path.isfile(key_path):
            raise KeyMissingException(reader)
        with open(key_path, "r") as f:
            private_key = self.RSA.importKey(f.read(), pw)
        return private_key.decrypt(b64decode(data))

def safe_json_load(fd):
    """
    wrapper for json.load() that will not throw an exception if the input file is empty
    """
    try:
        return json.load(fd)
    except ValueError, e:
        # this happens if the json can't be parsed
        if os.fstat(fd.fileno()).st_size == 0:
            # ok, default to empty password store
            return None
        else:
            # this is bad. There is unparsable data in the password file. Working
            # with an empty data store now could cause data loss. This requires
            # a human brain to fix
            raise

class ChangeContext(object):
    def __init__(self, filename, backend):
        super(ChangeContext, self).__init__()
        self.__filename = filename
        self.__backend = backend
        self.__fd = None
        self.__data = None

    def __enter__(self):
        try:
            self.__fd = open(self.__filename, "rw")
            fcntl.flock(self.__fd, fcntl.LOCK_EX)
            self.__data = safe_json_load(self.__fd) or PasswordStore.init_state.copy()
        except IOError, e:
            if e.errno == errno.ENOENT:
                self.__fd = open(self.__filename, "w")
                fcntl.flock(self.__fd, fcntl.LOCK_EX)
                self.__data = {}
            else:
                raise
        return self.__data

    def __exit__(self, typ, value, tb):
        if typ == None:
            self.__data['keydata'] = self.__backend.key_data()
            if 'secrets' not in self.__data:
                self.__data['secrets'] = {}
            with NamedTemporaryFile(dir=os.path.dirname(self.__filename), delete=False) as f:
                json.dump(self.__data, f)

            os.rename(f.name, self.__filename)
            fcntl.flock(self.__fd, fcntl.LOCK_UN)
            self.__fd.close()
            return True
        else:
            # let the exception continue
            return False


class PasswordStore(object):
    """
    The password store main class
    This class can (and should) be used in with-clause to ensure temporary data gets cleaned up

    Missing operations:
        - list all users
        - remove a user
        - change the password of a private key
    """

    init_state = {
        'secrets' : {}
    }

    def __init__(self, filename, backend):
        """
        constructor
        @param filename: name of the file to store passwords. Will be created if it doesn't exist
        @param backend: Encryption backend
        """
        self.__filename = filename
        self.__backend = backend
        self.__cache_time = 0
        self.__cache = None
        self.sync()

    def sync(self):
        try:
            st = os.stat(self.__filename)
            filetime = st.st_mtime
            if self.__cache is None or filetime > self.__cache_time:
                with open(self.__filename, "r") as f:
                    self.__cache = safe_json_load(f) or PasswordStore.init_state.copy()
        except (OSError, IOError), e:  # stat raises an OSError, open an IOError
            if e.errno == errno.ENOENT:
                # if the file doesn't exist, start with an empty store
                self.__cache = PasswordStore.init_state.copy()
            else:
                raise

        if self.__cache.get('keydata'):
            self.__backend.set_key_data(self.__cache['keydata'])


    def __enter__(self):
        return self

    def __exit__(self, typ, value, tb):
        self.__backend.cleanup()

    def list(self, user=None, with_details=False):
        """
        retrieve list of keys
        """
        secrets = None
        if user is None:
            secrets = list(self.__cache['secrets'].iteritems())
        else:
            secrets = [(k,v) for k, v in self.__cache['secrets'].iteritems() if user in v['data']]

        if with_details:
            return [{
                'key'    : s[0],
                'owner'  : s[1]['owner'],
                'shared' : s[1]['data'].keys()
            } for s in secrets]
        else:
            return [s[0] for s in secrets]

    def list_users(self):
        """
        retrive list of all users known in the keystore (this includes those for which
        the private key is not currently available)
        """
        return self.__backend.all_users()

    def add_user(self, user, passphrase):
        """
        add a user
        """
        with ChangeContext(self.__filename, self.__backend) as data:
            self.__backend.add_user(user, passphrase)

    def get(self, name, user):
        """
        retrive a secret
        @param name: name/key of the secret
        @param user: username to decrypt with
        @return: the decrypted secret
        """
        if name not in self.__cache['secrets']:
            raise InvalidKeyException(name)
        if user is None:
            # if user isn't set, try to retrieve with each reader.
            # As long as we have the private key for one, we're good
            for reader in self.__cache['secrets'][name]['data']:
                try:
                    return self.get(name, reader)
                except NotAuthorizedException:
                    pass
        else:
            if not user in self.__cache['secrets'][name]['data']:
                raise NotAuthorizedException(name, user)
            cipher = self.__cache['secrets'][name]['data'][user]
            return self.__backend.decrypt(cipher, user)

    def set(self, name, owner, secret):
        """
        set/change a secret
        @param name: name/key of the secret
        @param owner: username to be used as the owner
        @param secret: the secret to decrypt

        If this secret already exists, the encrypted data for all readers is updated. The owner
        has to be the owner of the existing data though -> this api can not be used to change
        the owner of a secret.
        """
        try:
            with ChangeContext(self.__filename, self.__backend) as data:
                if name not in data['secrets']:
                    if owner is None:
                        raise NotAuthorizedException(name, "<None>", "create")
                    data['secrets'][name] = {
                        'owner': owner,
                        'data': self.__backend.encrypt(secret, [owner])
                    }
                elif owner is not None and owner != data['secrets'][name]['owner']:
                    raise NotAuthorizedException(name, owner, "set")
                else:
                    # have to re-encrypt the secret for all readers
                    data['secrets'][name]['data'] =\
                        self.__backend.encrypt(secret, data['secrets'][name]['data'].keys())
                self.__cache = data
        except UnknownUserException, e:
            logging.error("user unknown: %s", e)

    def remove(self, name, owner):
        """
        remove a secret
        """
        with ChangeContext(self.__filename, self.__backend) as data:
            if name not in data['secrets']:
                raise InvalidKeyException(name)
            if owner != data['secrets'][name]['owner']:
                raise NotAuthorizedException(name, owner, "remove")
            del data['secrets'][name]
            self.__cache = data

    def share(self, name, readers):
        """
        share a secret with other users
        @param name: name/key of the secret
        @param readers: list of users that will gain access to the secret
        """
        with ChangeContext(self.__filename, self.__backend) as data:
            try:
                owner = data['secrets'][name]['owner']
            except KeyError:
                raise InvalidKeyException(name)
            secret = self.get(name, owner)
            data['secrets'][name]['data'].update(self.__backend.encrypt(secret, readers))
            self.__cache = data

    def unshare(self, name, readers):
        """
        stop sharing the secret with the specified users
        @param name: name/key ot the secret
        @param readers: list of users that will loose access to the secret

        Please note that it is not possible to unshare a secret with the owner unless
        this operation leaves no readers at all. In this case the secret is removed
        """
        # this is only to verify the caller has ownership rights to the key. Of course this
        # could be circumvented. Anyone with write access to the password store can destroy it
        # or remove access
        with ChangeContext(self.__filename, self.__backend) as data:
            owner = data['secrets'][name]['owner']
            self.get(name, owner)

            for reader_name in readers:
                if reader_name != owner:
                    del data['secrets'][name]['data'][reader_name]

            if owner in readers and len(data['secrets'][name]['data']) == 1:
                # if the call was to unshared the secret with all readers including the owner,
                # this would effectively remove the secret. We do just that.
                # Otherwise it is not possible to remove the owner from the readers list
                del data['secrets'][name]

            self.__cache = data


class NonePasswordProvider(object):
    def __init__(self):
        super(NonePasswordProvider, self).__init__()

    def __call__(self, user):
        return None


class PasswordQueryProvider(object):
    def __init__(self):
        super(PasswordQueryProvider, self).__init__()

    def __call__(self, user):
        from getpass import getpass
        return getpass("Please enter the password for \"%s\": " % user)

def do_action(store, args):
    try:
        if args.set is not None:
            if args.user is None:
                logging.error("You have to specify a user who will become owner of the secret")
            else:
                store.set(args.set[0], args.user, args.set[1])
                logging.info("key \"%s\" set with owner \"%s\"", args.set[0], args.user)
        elif args.get is not None:
            try:
                print(store.get(args.get, args.user))
            except NotAuthorizedException:
                logging.warn("User \"%s\" isn't authorized to retrive \"%s\"",
                                args.user, args.get)
        elif args.list:
            print("\n".join([
                "%s (owner %s, readable by %s)" %\
                (secret['key'], secret['owner'], ", ".join(secret['shared']))
                for secret in store.list(user=args.user, with_details=True)
            ]))
        elif args.listusers:
            print("\n".join(store.list_users()))
        elif args.share is not None:
            if len(args.share) < 2:
                logging.error("Expected at least 2 parameters, the name of the key and one user")
            else:
                try:
                    store.share(args.share[0], args.share[1:])
                    logging.info("allowing access to \"%s\" for %s",
                                args.share[0], ", ".join(["\"%s\"" % reader
                                                        for reader in args.share[1:]]))
                except UnknownUserException, e:
                    logging.error(e)
        elif args.unshare is not None:
            if len(args.unshare) < 2:
                logging.error("Expected at least 2 parameters, the name of the key and one user")
            else:
                try:
                    store.unshare(args.unshare[0], args.unshare[1:])
                    logging.info("removing access to \"%s\" for %s",
                                 args.unshare[0], ", ".join(["\"%s\"" % reader
                                                             for reader in args.unshare[1:]]))
                except UnknownUserException, e:
                    logging.error(e)
        elif args.adduser is not None:
            if args.interactive:
                from getpass import getpass
                password = getpass("Enter passphrase (or empty): ")
                if not password:
                    password = None
            else:
                password = None
            try:
                store.add_user(args.adduser, password)
                logging.info("user \"%s\" added %s password",
                             args.adduser, "without" if password is None else "with")
            except UserExistsException:
                logging.info("user \"%s\" exists already", args.adduser[0])
        else:
            logging.warn("No supported action")
    except KeyMissingException, e:
        logging.error("Authorization error: %s", e)


def main():
    parser = ArgumentParser()
    parser.add_argument("-g", "--get",
                        help="retrieve a secret. Any user with read-access to the secret has to "
                        "be set")
    parser.add_argument("-s", "--set", nargs=2,
                        help="set or change a secret. The owner has to be set with --user")
    parser.add_argument("-l", "--list", action='store_true',
                        help="list secrets. If a user is set with --user, only passwords that "
                        "user can read are listed")
    parser.add_argument("--listusers", action='store_true',
                        help="list all known users")
    parser.add_argument("--share", nargs='*',
                        help="share a secret with additional users.")
    parser.add_argument("--unshare", nargs='*',
                        help="stop sharing a secret with the specified users.")
    parser.add_argument("-u", "--user", help="specify the user for the operation. "
                        "For write operations this has to be the owner of the secret. "
                        "keydir has to contain the private key for this user.")
    parser.add_argument("-f", "--file", default="passwords.json",
                        help="The password file that stores all public keys and the encrypted "
                        "secrets")
    parser.add_argument("-k", "--keydir", default=os.path.join(os.environ.get("HOME", "/"), ".pwstore"),
                        help="Path to the private key directory. This directory is expected to "
                        "contain one pem-file per user.")
    parser.add_argument("--adduser", help="Add a user. This creates a new key-pair.")
    parser.add_argument("-v", "--verbose", action='store_true', help="Verbose output")
    parser.add_argument("-q", "--quiet", action='store_true', help="Silent output")
    parser.add_argument("-i", "--interactive", action='store_true', help="If true, interaction "
                        "is possible to enter passwords. If this is not set, it's not possible to "
                        "enter a password for adduser or to unlock any password protected private "
                        "key.")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    else:
        logging.getLogger().setLevel(logging.INFO)

    logging.debug("password file: %s", args.file)
    logging.debug("keys: %s" % args.keydir)

    if not os.path.exists(args.keydir):
        os.makedirs(args.keydir)
    elif os.path.isfile(args.keydir):
        logging.warn("keydir needs to be a directory, not a file")
        return 1

    if args.interactive:
        backend = CryptoBackend(args.keydir, PasswordQueryProvider())
    else:
        backend = CryptoBackend(args.keydir, NonePasswordProvider())
    with PasswordStore(args.file, backend) as store:
        do_action(store, args)

if __name__ == "__main__":
    main()
