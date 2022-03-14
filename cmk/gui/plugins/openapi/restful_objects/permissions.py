#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Endpoint permission system

It is currently only active for the REST API endpoints, but could be extended to the GUI endpoints

It does the following things:

 * when a permission is DECLARED on an endpoint:
   1. it ensures that the permission is actually known to the central permission_registry
   2. if an endpoint is executed:
       * it checks if the declared permission (or just some branch of it) is triggered.
       * see `cmk.gui.plugins.openapi.restful_objects.decorators.Endpoint.wrap_with_validation`
   3. if a permission is checked by the code which is executed during endpoint processing:
       * it ensures that this permission is DECLARED on the currently running endpoint
       * see `cmk.gui.utils.logged_in:LoggedInUser.may`

By this, we can make sure we always some understanding of the permissions required and used.

"""
from __future__ import annotations

import abc
import itertools
from typing import Iterable, List, Protocol, Sequence


class UserLike(Protocol):
    def has_permission(self, pname: str) -> bool:
        ...


class FakeUser:
    """Just something which looks like a user

    This is here, so we can have a simpler API for validate().

    """

    def __init__(
        self,
        perms: Sequence[str],
    ) -> None:
        self.perms = perms

    def has_permission(self, perm: str):
        return perm in self.perms


class BasePerm(abc.ABC):
    @abc.abstractmethod
    def may(self, user: UserLike):
        """Verify that this user fulfils the requirements."""
        raise NotImplementedError()

    @abc.abstractmethod
    def iter_perms(self) -> Iterable[str]:
        raise NotImplementedError

    def validate(self, permissions: Sequence[str]) -> bool:
        """Verify that a user with these permissions fulfills the requirements."""
        return self.may(FakeUser(permissions))

    def __contains__(self, item):
        return item in list(self.iter_perms())


class MultiPerm(BasePerm, abc.ABC):
    def __init__(self, perms: List[BasePerm]):
        self.perms = perms

    def __repr__(self):
        return f"{self.__class__.__name__}([{', '.join([repr(o) for o in self.perms])})"

    def iter_perms(self) -> Iterable[str]:
        return itertools.chain(*[perm.iter_perms() for perm in self.perms])


class NoPerm(BasePerm):
    """A permission which can never be held.

    This permission can never be true.
    """

    def may(self, user: UserLike) -> bool:
        """(Unsuccessfully) verify that the user fulfils the requirements.

        This method will never succeed in doing that though.
        """
        return False

    def iter_perms(self) -> Iterable[str]:
        return iter([])


class Perm(BasePerm):
    """A permission identified by a string."""

    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"{{{self.name}}}"

    def may(self, user: UserLike) -> bool:
        """Verify if the user fulfils the requirements.

        This method asks the user object if it has said permission."""
        return user.has_permission(self.name)

    def iter_perms(self) -> Iterable[str]:
        return iter([self.name])


class AllPerm(MultiPerm):
    """Represent a sequence of permissions in which ALL must be true to be valid

    The permissions in the collection may also be collections of more permissions.

    Examples:

        >>> p = AnyPerm([AllPerm([Perm("wato.edit"), Perm("wato.users")]), Perm("wato.seeall")])

        >>> class User:
        ...     def __init__(self, perms):
        ...         self.perms = perms
        ...     def has_permission(self, perm_name):
        ...         return perm_name in self.perms

        >>> p.may(User(["wato.edit"]))
        False

        >>> p.may(User(["wato.edit", "wato.users"]))
        True

        >>> p.may(User(["wato.users"]))
        False

        >>> p.may(User(["wato.seeall"]))
        True

    """

    def may(self, user: UserLike) -> bool:
        """Verify if the user fulfils the requirements.

        Is verified if all the child permissions are verified."""
        return all(perm.may(user) for perm in self.perms)


class AnyPerm(MultiPerm):
    """Represent a sequence of permissions in which JUST ONE need be true to be valid

    The permissions in the collection may also be collections of more permissions.

    Examples:

        >>> p = AnyPerm([Perm("foo"), AnyPerm([Perm("bar"), Perm("baz")])])

        >>> class User:
        ...     def __init__(self, perms):
        ...         self.perms = perms
        ...     def has_permission(self, perm_name):
        ...         return perm_name in self.perms

        >>> p.may(User(["foo"]))
        True

        >>> p.may(User(["bar"]))
        True

        >>> p.may(User(["baz"]))
        True

        >>> p.may(User(["FizzBuzz!"]))
        False

    """

    def may(self, user: UserLike) -> bool:
        """Verify if the user fulfils the requirements.

        Is verified if any one of the child permissions is verified."""
        return any(perm.may(user) for perm in self.perms)
