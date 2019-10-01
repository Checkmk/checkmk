#!/usr/bin/env python
# encoding: utf-8
# pylint: disable=redefined-outer-name

from pathlib2 import Path
import pytest  # type: ignore
from mockldap import MockLdap, LDAPObject  # type: ignore
import six

# userdb is needed to make the module register the post-config-load-hooks
import cmk.gui.userdb  # pylint: disable=unused-import
import cmk.gui.plugins.userdb.ldap_connector as ldap
import cmk.gui.plugins.userdb.utils as userdb_utils


def test_connector_info():
    assert ldap.LDAPUserConnector.type() == "ldap"
    assert "LDAP" in ldap.LDAPUserConnector.title()
    assert ldap.LDAPUserConnector.short_title() == "LDAP"


def test_connector_registered():
    assert userdb_utils.user_connector_registry.get("ldap") == ldap.LDAPUserConnector


def test_sync_plugins(load_config):
    assert sorted(ldap.ldap_attribute_plugin_registry.keys()) == sorted([
        'alias',
        'auth_expire',
        'email',
        'groups_to_attributes',
        'groups_to_contactgroups',
        'groups_to_roles',
        'disable_notifications',
        'force_authuser',
        'pager',
        'start_url',
        'ui_theme',
    ])


def _ldap_tree():
    tree = {
        "dc=org": {
            "objectclass": ["domain"],
            "objectcategory": ["domain"],
            "dn": ["dc=org"],
            "dc": "org",
        },
        "dc=check-mk,dc=org": {
            "objectclass": ["domain"],
            "objectcategory": ["domain"],
            "dn": ["dc=check-mk,dc=org"],
            "dc": "check-mk",
        },
        "ou=users,dc=check-mk,dc=org": {
            "objectclass": ["organizationalUnit"],
            "objectcategory": ["organizationalUnit"],
            "dn": ["ou=users,dc=check-mk,dc=org"],
            "ou": "users",
        },
        "ou=groups,dc=check-mk,dc=org": {
            "objectclass": ["organizationalUnit"],
            "objectcategory": ["organizationalUnit"],
            "dn": ["ou=groups,dc=check-mk,dc=org"],
            "ou": "groups",
        },
    }

    users = {
        "cn=admin,ou=users,dc=check-mk,dc=org": {
            "objectclass": ["user"],
            "objectcategory": ["person"],
            "dn": ["cn=admin,ou=users,dc=check-mk,dc=org"],
            "cn": ["Admin"],
            "samaccountname": ["admin"],
            "userPassword": ["ldap-test"],
            "mail": ["admin@check-mk.org"],
        },
        "cn=härry,ou=users,dc=check-mk,dc=org": {
            "objectclass": ["user"],
            "objectcategory": ["person"],
            "dn": ["cn=härry,ou=users,dc=check-mk,dc=org"],
            "cn": ["Härry Hörsch"],
            "samaccountname": ["härry"],
            "userPassword": ["ldap-test"],
            "mail": ["härry@check-mk.org"],
        },
        "cn=sync-user,ou=users,dc=check-mk,dc=org": {
            "objectclass": ["user"],
            "objectcategory": ["person"],
            "dn": ["cn=sync-user,ou=users,dc=check-mk,dc=org"],
            "cn": ["sync-user"],
            "samaccountname": ["sync-user"],
            "userPassword": ["sync-secret"],
        },
    }

    groups = {
        "cn=admins,ou=groups,dc=check-mk,dc=org": {
            "objectclass": ["group"],
            "objectcategory": ["group"],
            "dn": ["cn=admins,ou=groups,dc=check-mk,dc=org"],
            "cn": ["admins"],
            "member": ["cn=admin,ou=users,dc=check-mk,dc=org",],
        },
        u"cn=älle,ou=groups,dc=check-mk,dc=org": {
            "objectclass": ["group"],
            "objectcategory": ["group"],
            "dn": [u"cn=älle,ou=groups,dc=check-mk,dc=org"],
            "cn": ["alle"],
            "member": [
                "cn=admin,ou=users,dc=check-mk,dc=org",
                "cn=härry,ou=users,dc=check-mk,dc=org",
            ],
        },
        "cn=top-level,ou=groups,dc=check-mk,dc=org": {
            "objectclass": ["group"],
            "objectcategory": ["group"],
            "dn": ["cn=top-level,ou=groups,dc=check-mk,dc=org"],
            "cn": ["top-level"],
            "member": [
                "cn=level1,ou=groups,dc=check-mk,dc=org",
                "cn=sync-user,ou=users,dc=check-mk,dc=org",
            ],
        },
        "cn=level1,ou=groups,dc=check-mk,dc=org": {
            "objectclass": ["group"],
            "objectcategory": ["group"],
            "dn": ["cn=level1,ou=groups,dc=check-mk,dc=org"],
            "cn": ["level1"],
            "member": ["cn=level2,ou=groups,dc=check-mk,dc=org",],
        },
        "cn=level2,ou=groups,dc=check-mk,dc=org": {
            "objectclass": ["group"],
            "objectcategory": ["group"],
            "dn": ["cn=level2,ou=groups,dc=check-mk,dc=org"],
            "cn": ["level2"],
            "member": [
                "cn=admin,ou=users,dc=check-mk,dc=org",
                "cn=härry,ou=users,dc=check-mk,dc=org",
            ],
        },
        "cn=loop1,ou=groups,dc=check-mk,dc=org": {
            "objectclass": ["group"],
            "objectcategory": ["group"],
            "dn": ["cn=loop1,ou=groups,dc=check-mk,dc=org"],
            "cn": ["loop1"],
            "member": [
                "cn=admin,ou=users,dc=check-mk,dc=org",
                "cn=loop2,ou=groups,dc=check-mk,dc=org",
            ],
        },
        "cn=loop2,ou=groups,dc=check-mk,dc=org": {
            "objectclass": ["group"],
            "objectcategory": ["group"],
            "dn": ["cn=loop2,ou=groups,dc=check-mk,dc=org"],
            "cn": ["loop2"],
            "member": ["cn=loop3,ou=groups,dc=check-mk,dc=org",],
        },
        "cn=loop3,ou=groups,dc=check-mk,dc=org": {
            "objectclass": ["group"],
            "objectcategory": ["group"],
            "dn": ["cn=loop3,ou=groups,dc=check-mk,dc=org"],
            "cn": ["loop3"],
            "member": [
                "cn=loop1,ou=groups,dc=check-mk,dc=org",
                "cn=härry,ou=users,dc=check-mk,dc=org",
            ],
        },
        "cn=empty,ou=groups,dc=check-mk,dc=org": {
            "objectclass": ["group"],
            "objectcategory": ["group"],
            "dn": ["cn=empty,ou=groups,dc=check-mk,dc=org"],
            "cn": ["empty"],
            "member": [],
        },
        "cn=member-out-of-scope,ou=groups,dc=check-mk,dc=org": {
            "objectclass": ["group"],
            "objectcategory": ["group"],
            "dn": ["cn=member-out-of-scope,ou=groups,dc=check-mk,dc=org"],
            "cn": ["member-out-of-scope"],
            "member": ["cn=nono,ou=out-of-scope,dc=check-mk,dc=org",],
        },
        "cn=out-of-scope,dc=check-mk,dc=org": {
            "objectclass": ["group"],
            "objectcategory": ["group"],
            "dn": ["cn=out-of-scope,ou=groups,dc=check-mk,dc=org"],
            "cn": ["out-of-scope"],
            "member": ["cn=admin,ou=users,dc=check-mk,dc=org",],
        },
    }

    tree.update(users)
    tree.update(groups)

    # Dynamically patch memberOf attribute into the user objects to make checking
    # of nested group memberships work without redundancy
    for group_dn, group in sorted(groups.items()):
        for member_dn in group["member"]:
            if member_dn in tree:
                tree[member_dn].setdefault("memberof", []).append(group_dn)

    return tree


def encode_to_byte_strings(inp):
    if isinstance(inp, dict):
        return {
            encode_to_byte_strings(key): encode_to_byte_strings(value)
            for key, value in inp.iteritems()
        }
    elif isinstance(inp, list):
        return [encode_to_byte_strings(element) for element in inp]
    elif isinstance(inp, tuple):
        return tuple([encode_to_byte_strings(element) for element in inp])
    elif isinstance(inp, six.text_type):
        return inp.encode("utf-8")
    return inp


@pytest.fixture(scope="module", autouse=True)
def user_files():
    profile_dir = Path(cmk.utils.paths.var_dir, "web", "admin")
    profile_dir.mkdir(parents=True, exist_ok=True)
    with profile_dir.joinpath("cached_profile.mk").open("w", encoding="utf-8") as f:  # pylint: disable=no-member
        f.write(u"%r" % {
            "alias": u"admin",
            "connector": "default",
        })

    Path(cmk.utils.paths.htpasswd_file).parent.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member
    with open(cmk.utils.paths.htpasswd_file, "w") as f:
        f.write(
            "automation:$5$rounds=535000$eDIHah5PgsY2widK$tiVBvDgq0Nwxy5zd/oNFRZ8faTlOPA2T.tx.lTeQoZ1\n"
            "cmkadmin:Sl94oMGDJB/wQ\n")


@pytest.fixture()
def mocked_ldap(monkeypatch):
    ldap_mock = MockLdap(_ldap_tree())

    def connect(self, enforce_new=False, enforce_server=None):
        self._default_bind(self._ldap_obj)

    monkeypatch.setattr(ldap.LDAPUserConnector, "connect", connect)
    monkeypatch.setattr(ldap.LDAPUserConnector, "disconnect", lambda self: None)

    ldap_connection = ldap.LDAPUserConnector({
        "id": "default",
        "type": "ldap",
        "description": "Test connection",
        "disabled": False,
        "cache_livetime": 300,
        "suffix": "testldap",
        "active_plugins": {
            'email': {},
            'alias': {},
            'auth_expire': {}
        },
        "directory_type": ("ad", {
            "connect_to": ("fixed_list", {
                "server": "127.0.0.1"
            }),
        }),
        "bind": ("cn=sync-user,ou=users,dc=check-mk,dc=org", "sync-secret"),
        "user_id_umlauts": "keep",
        "user_scope": "sub",
        "user_dn": "ou=users,dc=check-mk,dc=org",
        "group_dn": "ou=groups,dc=check-mk,dc=org",
        "group_scope": "sub",
    })

    ldap_mock.start()
    ldap_connection._ldap_obj = ldap_mock["ldap://127.0.0.1"]

    def search_ext(self,
                   base,
                   scope,
                   filterstr='(objectclass=*)',
                   attrlist=None,
                   attrsonly=0,
                   serverctrls=None):

        # MockLdap does not exactly behave like python ldap library in terms of
        # encoding. The latter want's to have byte encoded strings and MockLdap
        # wants unicode strings :-/. Prepare the data we normally send to
        # python-ldap for MockLdap here.
        if not isinstance(base, six.text_type):
            base = base.decode("utf-8")

        if not isinstance(filterstr, six.text_type):
            filterstr = filterstr.decode("utf-8")

        return self.search(base, scope, filterstr, attrlist, attrsonly)

    LDAPObject.search_ext = search_ext

    def result_3(self, *args, **kwargs):
        unused_code, response, unused_msgid, serverctrls = \
            tuple(list(LDAPObject.result(self, *args, **kwargs)) + [None, []])
        return unused_code, encode_to_byte_strings(response), unused_msgid, serverctrls

    LDAPObject.result3 = result_3

    return ldap_connection


def _check_restored_bind_user(mocked_ldap):
    assert mocked_ldap._ldap_obj.whoami_s() == "dn:cn=sync-user,ou=users,dc=check-mk,dc=org"


def test_check_credentials_success(mocked_ldap):
    result = mocked_ldap.check_credentials("admin", "ldap-test")
    assert isinstance(result, six.text_type)
    assert result == "admin"

    result = mocked_ldap.check_credentials(u"admin", "ldap-test")
    assert isinstance(result, six.text_type)
    assert result == "admin"
    _check_restored_bind_user(mocked_ldap)


def test_check_credentials_invalid(mocked_ldap):
    assert mocked_ldap.check_credentials("admin", "WRONG") is False
    _check_restored_bind_user(mocked_ldap)


def test_check_credentials_not_existing(mocked_ldap):
    assert mocked_ldap.check_credentials("john", "secret") is None
    _check_restored_bind_user(mocked_ldap)


def test_check_credentials_enforce_conn_success(mocked_ldap):
    result = mocked_ldap.check_credentials("admin@testldap", "ldap-test")
    assert isinstance(result, six.text_type)
    assert result == "admin"
    _check_restored_bind_user(mocked_ldap)


def test_check_credentials_enforce_invalid(mocked_ldap):
    assert mocked_ldap.check_credentials("admin@testldap", "WRONG") is False
    _check_restored_bind_user(mocked_ldap)


def test_check_credentials_enforce_not_existing(mocked_ldap):
    assert mocked_ldap.check_credentials("john@testldap", "secret") is False
    _check_restored_bind_user(mocked_ldap)


def test_object_exists(mocked_ldap):
    assert mocked_ldap.object_exists("dc=org") is True
    assert mocked_ldap.object_exists("dc=XYZ") is False
    assert mocked_ldap.object_exists("ou=users,dc=check-mk,dc=org") is True
    assert mocked_ldap.object_exists("cn=admin,ou=users,dc=check-mk,dc=org") is True
    assert mocked_ldap.object_exists("cn=admins,ou=groups,dc=check-mk,dc=org") is True


def test_user_base_dn_exists(mocked_ldap):
    assert mocked_ldap.user_base_dn_exists()


def test_user_base_dn_not_exists(mocked_ldap, monkeypatch):
    monkeypatch.setattr(mocked_ldap, "_get_user_dn", lambda: "ou=users-nono,dc=check-mk,dc=org")
    assert not mocked_ldap.user_base_dn_exists()


def test_group_base_dn_exists(mocked_ldap):
    assert mocked_ldap.group_base_dn_exists()


def test_group_base_dn_not_exists(mocked_ldap, monkeypatch):
    monkeypatch.setattr(mocked_ldap, "get_group_dn", lambda: "ou=groups-nono,dc=check-mk,dc=org")
    assert not mocked_ldap.group_base_dn_exists()


def test_locked_attributes(mocked_ldap):
    assert set(mocked_ldap.locked_attributes()) == {'alias', 'password', 'locked', 'email'}


def test_multisite_attributes(mocked_ldap):
    assert mocked_ldap.multisite_attributes() == ['ldap_pw_last_changed']


def test_non_contact_attributes(mocked_ldap):
    assert mocked_ldap.non_contact_attributes() == ['ldap_pw_last_changed']


def test_get_users(mocked_ldap):
    users = mocked_ldap.get_users()
    assert len(users) == 3

    assert u"härry" in users
    assert "admin" in users
    assert "sync-user" in users

    assert users[u"härry"] == {
        'dn': u'cn=h\xe4rry,ou=users,dc=check-mk,dc=org',
        'mail': [u'h\xe4rry@check-mk.org'],
        'samaccountname': [u'h\xe4rry'],
        'cn': [u'H\xe4rry H\xf6rsch']
    }


@pytest.mark.parametrize("nested", [True, False])
def test_get_group_memberships_simple(mocked_ldap, nested):
    assert mocked_ldap.get_group_memberships(["admins"], nested=nested) == {
        u'cn=admins,ou=groups,dc=check-mk,dc=org': {
            'cn': u'admins',
            'members': [u'cn=admin,ou=users,dc=check-mk,dc=org'],
        }
    }


@pytest.mark.parametrize("nested", [True, False])
def test_get_group_memberships_flat_out_of_scope(mocked_ldap, nested):
    assert mocked_ldap.get_group_memberships(["out-of-scope"], nested=nested) == {}


# TODO: Currently failing. Need to fix the code.
#def test_get_group_memberships_out_of_scope_member(mocked_ldap):
#    assert mocked_ldap.get_group_memberships(["member-out-of-scope"]) == {
#        u'cn=member-out-of-scope,ou=groups,dc=check-mk,dc=org': {
#            'cn': u'member-out-of-scope',
#            'members': [
#            ],
#        }
#    }
#
#
#def test_get_group_memberships_flat_skip_group(mocked_ldap):
#    assert mocked_ldap.get_group_memberships(["top-level"]) == {
#        u'cn=top-level,ou=groups,dc=check-mk,dc=org': {
#            'cn': u'top-level',
#            'members': [
#                u"cn=sync-user,ou=users,dc=check-mk,dc=org",
#            ],
#        }
#    }


@pytest.mark.parametrize("nested", [True, False])
def test_get_group_memberships_with_non_ascii(mocked_ldap, nested):
    assert mocked_ldap.get_group_memberships(["alle"], nested=nested) == {
        u'cn=älle,ou=groups,dc=check-mk,dc=org': {
            'cn': u'alle',
            'members': [
                u'cn=admin,ou=users,dc=check-mk,dc=org',
                u'cn=härry,ou=users,dc=check-mk,dc=org',
            ],
        }
    }


@pytest.mark.parametrize("nested", [True, False])
def test_get_group_memberships_not_existing(mocked_ldap, nested):
    assert mocked_ldap.get_group_memberships(["not-existing"], nested=nested) == {}


def test_get_group_memberships_nested(mocked_ldap):
    memberships = mocked_ldap.get_group_memberships(["empty", "top-level", "level1", "level2"],
                                                    nested=True)

    assert len(memberships) == 4

    needed_groups = [
        (u'cn=empty,ou=groups,dc=check-mk,dc=org', {
            'cn': u'empty',
            'members': [],
        }),
        (u'cn=level2,ou=groups,dc=check-mk,dc=org', {
            'cn': u'level2',
            'members': [
                u"cn=admin,ou=users,dc=check-mk,dc=org",
                u"cn=härry,ou=users,dc=check-mk,dc=org",
            ],
        }),
        (u'cn=level1,ou=groups,dc=check-mk,dc=org', {
            'cn': u'level1',
            'members': [
                u"cn=admin,ou=users,dc=check-mk,dc=org",
                u"cn=härry,ou=users,dc=check-mk,dc=org",
            ],
        }),
        (u'cn=top-level,ou=groups,dc=check-mk,dc=org', {
            'cn': u'top-level',
            'members': [
                u"cn=admin,ou=users,dc=check-mk,dc=org",
                u"cn=härry,ou=users,dc=check-mk,dc=org",
                u"cn=sync-user,ou=users,dc=check-mk,dc=org",
            ],
        }),
    ]

    for needed_group_dn, needed_group in needed_groups:
        assert memberships[needed_group_dn] == needed_group
