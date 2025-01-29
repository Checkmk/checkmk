#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Endpoint permission system

The endpoint permission system, currently active for REST API endpoints and potentially extendable
to GUI endpoints, performs the following:

 1. Verifies declared permissions against the central permission registry.
 2. Upon endpoint execution, checks if the declared permission (or a part of it) is triggered.
     * see `cmk.gui.openapi.restful_objects.decorators.Endpoint.wrap_with_validation`
 3. Ensures permission checked during endpoint processing are declared for the running endpoint.
     * see `cmk.gui.utils.logged_in:LoggedInUser.may`

With this, we can ensure we always have some understanding of the required and used permissions.

"""

from __future__ import annotations

import abc
import itertools
from collections.abc import Iterable, Sequence
from typing import Protocol


class UserLike(Protocol):
    def has_permission(self, pname: str) -> bool: ...


class FakeUser:
    """Just something which looks like a user

    This is here, so we can have a simpler API for validate().

    """

    def __init__(
        self,
        perms: Sequence[str],
    ) -> None:
        self.perms = perms

    def has_permission(self, perm: str) -> bool:
        return perm in self.perms


class BasePerm(abc.ABC):
    @abc.abstractmethod
    def has_permission(self, user: UserLike) -> bool:
        """Verify that this user fulfils the requirements."""
        raise NotImplementedError()

    @abc.abstractmethod
    def iter_perms(self) -> Iterable[Perm]:
        raise NotImplementedError

    def validate(self, permissions: Sequence[str]) -> bool:
        """Verify that a user with these permissions fulfills the requirements."""
        return self.has_permission(FakeUser(permissions))

    def __contains__(self, item):
        return item in (p.name for p in self.iter_perms())


class Optional(BasePerm):
    """A permission which might or might not be used.

    Both of these cases are valid, so it always returns True.
    """

    def __init__(self, perm: BasePerm) -> None:
        self.perm = perm

    def __repr__(self) -> str:
        return f"{self.perm}?"

    def has_permission(self, user: UserLike) -> bool:
        """Verify that the permission might be there or not.

        It's okay if we don't have the permission, so we accept it all the time."""
        return True

    def iter_perms(self) -> Iterable[Perm]:
        return self.perm.iter_perms()


class Undocumented(Optional):
    """A permission which shall not be documented, but may occur.

    Structurally similar to `Optional` but with a different name."""


class MultiPerm(BasePerm, abc.ABC):
    def __init__(self, perms: list[BasePerm]) -> None:
        self.perms = perms

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}([{', '.join([repr(o) for o in self.perms])})"

    def iter_perms(self) -> Iterable[Perm]:
        return itertools.chain(*[perm.iter_perms() for perm in self.perms])


class NoPerm(BasePerm):
    """A permission which can never be held.

    This permission can never be true.
    """

    def has_permission(self, user: UserLike) -> bool:
        """(Unsuccessfully) verify that the user fulfils the requirements.

        This method will never succeed in doing that though.
        """
        return False

    def iter_perms(self) -> Iterable[Perm]:
        return iter([])


class Perm(BasePerm):
    """A permission identified by a string."""

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"{{{self.name}}}"

    def has_permission(self, user: UserLike) -> bool:
        """Verify if the user fulfils the requirements.

        This method asks the user object if it has said permission."""
        return user.has_permission(self.name)

    def iter_perms(self) -> Iterable[Perm]:
        return iter([self])


class AllPerm(MultiPerm):
    """Represent a sequence of permissions in which ALL must be true to be valid

    The permissions in the collection may also be collections of more permissions.

    Examples:

        >>> p = AnyPerm([AllPerm([Perm("wato.edit"), Perm("wato.users")]), Perm("wato.seeall")])

        >>> class User:
        ...     def __init__(self, perms) -> None:
        ...         self.perms = perms
        ...     def has_permission(self, perm_name) -> bool:
        ...         return perm_name in self.perms

        >>> p.has_permission(User(["wato.edit"]))
        False

        >>> p.has_permission(User(["wato.edit", "wato.users"]))
        True

        >>> p.has_permission(User(["wato.users"]))
        False

        >>> p.has_permission(User(["wato.seeall"]))
        True

        >>> "wato.seeall" in p
        True

        >>> "foo.bar" in p
        False

    """

    def has_permission(self, user: UserLike) -> bool:
        """Verify if the user fulfils the requirements.

        Is verified if all the child permissions are verified."""
        return all(perm.has_permission(user) for perm in self.perms)


class AnyPerm(MultiPerm):
    """Represent a sequence of permissions in which JUST ONE need be true to be valid

    The permissions in the collection may also be collections of more permissions.

    Examples:

        >>> p = AnyPerm([Perm("foo"), AnyPerm([Perm("bar"), Perm("baz")])])

        >>> class User:
        ...     def __init__(self, perms) -> None:
        ...         self.perms = perms
        ...     def has_permission(self, perm_name) -> bool:
        ...         return perm_name in self.perms

        >>> p.has_permission(User(["foo"]))
        True

        >>> p.has_permission(User(["bar"]))
        True

        >>> p.has_permission(User(["baz"]))
        True

        >>> p.has_permission(User(["FizzBuzz!"]))
        False

    """

    def has_permission(self, user: UserLike) -> bool:
        """Verify if the user fulfils the requirements.

        Is verified if any one of the child permissions is verified."""
        return any(perm.has_permission(user) for perm in self.perms)


class OkayToIgnorePerm(Perm):
    """A permission which does not raise an error if it is not present in Checkmk during built-time.

    Introduced mainly since some components were removed in the CSE edition. Removing a
    component also removes the associating permissions. Some general endpoints make use of
    those permissions beyond its component specific endpoints and this would lead to an error
    if the permission is not present. This permission will also not get rendered in the
    documentation.

    Consider this as a workaround since clear separation of edition specific permissions would
    require a restructure of the entire endpoint specific permissions specification system.
    """
