#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import pickle
from collections.abc import Callable, Sequence
from contextlib import suppress
from pathlib import Path
from typing import Any, cast, Final, Generic, get_args, TypeVar

import cmk.ccc.version as cmk_version
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.store import save_object_to_file
from cmk.ccc.user import UserId

import cmk.utils
import cmk.utils.paths
from cmk.utils.escaping import escape

from cmk.gui import userdb
from cmk.gui.config import active_config, default_authorized_builtin_role_ids
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import save_user_file, user
from cmk.gui.permissions import declare_permission, permission_registry
from cmk.gui.type_defs import PermissionName, RoleName, Visual, VisualName, VisualTypeName
from cmk.gui.utils.roles import user_may
from cmk.gui.utils.speaklater import LazyString

from cmk.mkp_tool import id_to_mkp, Installer, PackageName, PackagePart

TVisual = TypeVar("TVisual", bound=Visual)
CustomUserVisuals = dict[tuple[UserId, VisualName], TVisual]

__all__ = [
    "save",
    "load",
    "declare_custom_permissions",
    "available",
    "get_permissioned_visual",
    "move_visual_to_local",
    "delete_local_file",
    "get_installed_packages",
    "TVisual",
    "local_file_exists",
    "load_visuals_of_a_user",
]


def save(
    what: VisualTypeName,
    visuals: dict[tuple[UserId, VisualName], TVisual],
    user_id: UserId | None = None,
) -> None:
    if user_id is None:
        user_id = user.ident

    user_visuals = {
        # Since we're de/serializing the Visuals via literal_eval/repr, we will not be able to
        # deserialize LasyStrings again. Decide on their fixed str representation now.
        name: _fix_lazy_strings(visual)
        for (owner_id, name), visual in visuals.items()
        if user_id == owner_id and not visual["packaged"]
    }
    save_user_file("user_" + what, user_visuals, user_id=user_id)
    _CombinedVisualsCache(what).invalidate_cache()


def load(
    what: VisualTypeName,
    builtin_visuals: dict[VisualName, TVisual],
    internal_to_runtime_transformer: Callable[[dict[str, Any]], TVisual],
) -> dict[tuple[UserId, VisualName], TVisual]:
    visuals = {
        # Ensure converting _l to str. During "import time" the may not be localized since the
        # user language is not known. Here we are in a request context and may resolve the
        # localization. It might be better to keep the LazyString objects unresolved during run
        # time, but we had some call sites which were not correctly handling the LazyStrings. So
        # we took the approach to resolve them in a central early stage instead.
        (UserId.builtin(), name): _fix_lazy_strings(visual)
        for name, visual in builtin_visuals.items()
    }

    # Add custom "user_*.mk" visuals
    visuals.update(
        _CombinedVisualsCache[TVisual](what).load(
            internal_to_runtime_transformer,
        )
    )

    return visuals


def _fix_lazy_strings(obj: TVisual) -> TVisual:
    """
    Recursively evaluate all LazyStrings in the object to fixed strings by running them through str()
    """

    def _fix(value: object) -> object:
        if isinstance(value, dict):
            return {attr: _fix(element) for attr, element in value.items()}
        if isinstance(value, list):
            return [_fix(element) for element in value]
        if isinstance(value, tuple):
            return tuple(_fix(element) for element in value)
        if isinstance(value, LazyString):
            return str(value)
        return value

    return cast(TVisual, {attr: _fix(value) for attr, value in obj.items()})


class _CombinedVisualsCache(Generic[TVisual]):
    _visuals_cache_dir: Final = cmk.utils.paths.visuals_cache_dir

    def __init__(self, visual_type: VisualTypeName) -> None:
        self._visual_type: Final = visual_type

    @classmethod
    def invalidate_all_caches(cls) -> None:
        for visual_type in get_args(VisualTypeName):
            _CombinedVisualsCache(visual_type).invalidate_cache()

    def invalidate_cache(self) -> None:
        self._info_filename.unlink(missing_ok=True)

    def _update_cache_info_timestamp(self) -> None:
        cache_info_filename = self._info_filename
        cache_info_filename.parent.mkdir(parents=True, exist_ok=True)
        cache_info_filename.touch()

    @property
    def _info_filename(self) -> Path:
        return self._visuals_cache_dir / f"last_update_{self._visual_type}"

    @property
    def _content_filename(self) -> Path:
        return self._visuals_cache_dir / f"cached_{self._visual_type}"

    def load(
        self,
        internal_to_runtime_transformer: Callable[[dict[str, Any]], TVisual],
    ) -> CustomUserVisuals:
        if self._may_use_cache():
            if (content := self._read_from_cache()) is not None:
                self._set_permissions(content)
                return content
        return self._compute_and_write_cache(internal_to_runtime_transformer)

    def _set_permissions(self, content: CustomUserVisuals) -> None:
        """Make sure that all permissions are known to the current apache process"""
        for name, visual in content.items():
            declare_visual_permission(self._visual_type, name[1], visual)
            if visual["packaged"]:
                declare_packaged_visual_permission(self._visual_type, name[1], visual)

    def _may_use_cache(self) -> bool:
        if not self._content_filename.exists():
            return False

        if not self._info_filename.exists():
            # Create a new file for future reference (this obviously has the newest timestamp)
            self._update_cache_info_timestamp()
            return False

        try:
            if self._content_filename.stat().st_mtime < self._info_filename.stat().st_mtime:
                return False
        except FileNotFoundError:
            return False

        return True

    def _compute_and_write_cache(
        self,
        internal_to_runtime_transformer: Callable[[dict[str, Any]], TVisual],
    ) -> CustomUserVisuals:
        visuals = _load_custom_user_visuals(self._visual_type, internal_to_runtime_transformer)
        self._write_to_cache(visuals)
        return visuals

    def _read_from_cache(self) -> CustomUserVisuals | None:
        try:
            return store.load_object_from_pickle_file(self._content_filename, default={})
        except (TypeError, pickle.UnpicklingError):
            return None

    def _write_to_cache(self, visuals: CustomUserVisuals) -> None:
        store.save_bytes_to_file(self._content_filename, pickle.dumps(visuals))
        self._update_cache_info_timestamp()


def invalidate_all_caches() -> None:
    _CombinedVisualsCache.invalidate_all_caches()


def _load_custom_user_visuals(
    what: VisualTypeName,
    internal_to_runtime_transformer: Callable[[dict[str, Any]], TVisual],
) -> CustomUserVisuals:
    """Note: Try NOT to use pathlib.Path functionality in this function, as pathlib is
    measurably slower (7 times), due to path object creation and concatenation. This function
    can iterate over several thousand files, which may take 250ms (Path) or 50ms(os.path)"""

    visuals: CustomUserVisuals = {}
    visual_filename = "user_%s.mk" % what
    old_views_filename = "views.mk"

    for dirname in cmk.utils.paths.profile_dir.iterdir():
        try:
            user_dirname = os.path.join(cmk.utils.paths.profile_dir, dirname)
            visual_path = os.path.join(user_dirname, visual_filename)
            # Be compatible to old views.mk. The views.mk contains customized views
            # in an old format which will be loaded, transformed and when saved stored
            # in users_views.mk. When this file exists only this file is used.
            if what == "views" and not os.path.exists(visual_path):
                visual_path = os.path.join(user_dirname, old_views_filename)

            if not os.path.exists(visual_path):
                continue

            user_id = os.path.basename(dirname)
            if not userdb.user_exists(UserId(user_id)):
                continue

            visuals.update(
                load_visuals_of_a_user(
                    what,
                    internal_to_runtime_transformer,
                    Path(visual_path),
                    UserId(user_id),
                )
            )

        except SyntaxError as e:
            raise MKGeneralException(_("Cannot load %s from %s: %s") % (what, visual_path, e))

    visuals.update(
        _get_packaged_visuals(
            what,
            internal_to_runtime_transformer,
        )
    )

    return visuals


def load_visuals_of_a_user(
    what: VisualTypeName,
    internal_to_runtime_transformer: Callable[[dict[str, Any]], TVisual],
    path: Path,
    user_id: UserId,
) -> CustomUserVisuals[TVisual]:
    user_visuals: CustomUserVisuals[TVisual] = {}
    for name, raw_visual in store.try_load_file_from_pickle_cache(
        path, default={}, temp_dir=cmk.utils.paths.tmp_dir, root_dir=cmk.utils.paths.omd_root
    ).items():
        visual = internal_to_runtime_transformer(raw_visual)
        visual["owner"] = user_id
        visual["name"] = name

        # Declare custom permissions
        declare_visual_permission(what, name, visual)

        user_visuals[(user_id, name)] = visual

    return user_visuals


def load_raw_visuals_of_a_user(
    what: VisualTypeName,
    user_id: UserId,
) -> dict[str, dict[str, Any]]:
    path = cmk.utils.paths.profile_dir / user_id / f"user_{what}.mk"
    return store.try_load_file_from_pickle_cache(
        path, default={}, temp_dir=cmk.utils.paths.tmp_dir, root_dir=cmk.utils.paths.omd_root
    )


def _get_packaged_visuals(
    visual_type: VisualTypeName,
    internal_to_runtime_transformer: Callable[[dict[str, Any]], TVisual],
) -> CustomUserVisuals[TVisual]:
    local_visuals: CustomUserVisuals[TVisual] = {}
    local_path = _get_local_path(visual_type)
    for dirpath in local_path.iterdir():
        if dirpath.is_dir():
            continue

        try:
            for name, raw_visual in store.try_load_file_from_pickle_cache(
                dirpath,
                default={},
                temp_dir=cmk.utils.paths.tmp_dir,
                root_dir=cmk.utils.paths.omd_root,
            ).items():
                visual = internal_to_runtime_transformer(raw_visual)
                visual["owner"] = UserId.builtin()
                visual["name"] = name
                visual["packaged"] = True

                # Declare custom permissions
                declare_packaged_visual_permission(visual_type, name, visual)

                local_visuals[(UserId.builtin(), name)] = visual
        except Exception:
            logger.exception(
                "Error on loading packaged visuals from file %s. Skipping it...", dirpath
            )
    return local_visuals


def get_installed_packages(what: VisualTypeName) -> dict[str, PackageName | None]:
    return (
        {}
        if cmk_version.edition(cmk.utils.paths.omd_root) is cmk_version.Edition.CRE
        or not user.may("wato.manage_mkps")
        else id_to_mkp(
            Installer(cmk.utils.paths.installed_packages_dir),
            _all_local_visuals_files(what),
            PackagePart.GUI,
        )
    )


def _all_local_visuals_files(what: VisualTypeName) -> set[Path]:
    local_path = _get_local_path(what)
    # dashboard dir is singular in local web and gui folder
    dir_name = "dashboard" if what == "dashboards" else what
    with suppress(FileNotFoundError):
        return {
            Path(dir_name) / f.relative_to(local_path)
            for f in local_path.iterdir()
            if not f.is_dir()
        }
    return set()


def move_visual_to_local(
    visual_id: str,
    owner: UserId,
    all_visuals: dict[tuple[UserId, VisualName], TVisual],
    visual_type: VisualTypeName,
) -> None:
    """Create a file within ~/local with content of the visual"""
    local_path = _get_local_path(visual_type)

    if source_visual := all_visuals.get((owner, visual_id)):
        visual = {}
        visual[visual_id] = source_visual
        if "owner" in visual[visual_id]:
            del visual[visual_id]["owner"]

        save_object_to_file(
            path=local_path / visual_id,
            data=visual,
            pprint_value=True,
        )
    _CombinedVisualsCache(visual_type).invalidate_cache()


def delete_local_file(visual_type: VisualTypeName, visual_name: str) -> None:
    visuals_path = _get_local_path(visual_type) / visual_name
    visuals_path.unlink(missing_ok=True)
    _CombinedVisualsCache(visual_type).invalidate_cache()


def local_file_exists(visual_type: VisualTypeName, visual_name: str) -> bool:
    return Path(_get_local_path(visual_type) / visual_name).exists()


def _get_local_path(visual_type: VisualTypeName) -> Path:
    match visual_type:
        case "dashboards":
            local_path = cmk.utils.paths.local_dashboards_dir
        case "views":
            local_path = cmk.utils.paths.local_views_dir
        case "reports":
            local_path = cmk.utils.paths.local_reports_dir
        case _:
            raise MKUserError(None, _("This package type is not supported."))

    # The directory can be removed during deinstallation of MKPs (SUP-23400).
    # To avoid a crash in the GUI we ensure that the directory exists (CMK-23624).
    local_path.mkdir(parents=True, exist_ok=True)
    return local_path


def _get_dynamic_visual_default_permissions() -> Sequence[RoleName]:
    if active_config.default_dynamic_visual_permission == "yes":
        return default_authorized_builtin_role_ids
    return ["admin"]


def declare_visual_permission(what: VisualTypeName, name: str, visual: TVisual) -> None:
    permname = PermissionName(f"{what[:-1]}.{name}")
    if published_to_user(visual) and permname not in permission_registry:
        declare_permission(
            permname,
            f"{visual['title']} ({visual['name']})",
            visual["description"],
            _get_dynamic_visual_default_permissions(),
        )


def declare_packaged_visual_permission(what: VisualTypeName, name: str, visual: TVisual) -> None:
    permname = PermissionName(f"{what[:-1]}.{name}_packaged")
    if visual["packaged"] and permname not in permission_registry:
        declare_permission(
            permname,
            f"{visual['title']} ({visual['name']}, {_('packaged)')}",
            visual["description"],
            _get_dynamic_visual_default_permissions(),
        )


# Load all users visuals just in order to declare permissions of custom visuals
# TODO: Use regular load logic here, e.g. _load_custom_user_visuals()
def declare_custom_permissions(what: VisualTypeName) -> None:
    for dirpath in cmk.utils.paths.profile_dir.iterdir():
        try:
            if dirpath.is_dir():
                path = dirpath.joinpath("user_%s.mk" % what)
                if not path.exists():
                    continue
                visuals = store.load_object_from_file(path, default={})
                for name, visual in visuals.items():
                    declare_visual_permission(what, name, visual)
        except Exception:
            logger.exception(
                "Error on declaring permissions for customized visuals in file %s", dirpath
            )
            if active_config.debug:
                raise


def declare_packaged_visuals_permissions(what: VisualTypeName) -> None:
    for dirpath in _get_local_path(what).iterdir():
        try:
            if dirpath.is_dir():
                continue

            for name, visual in store.try_load_file_from_pickle_cache(
                dirpath,
                default={},
                temp_dir=cmk.utils.paths.tmp_dir,
                root_dir=cmk.utils.paths.omd_root,
            ).items():
                visual["packaged"] = True
                declare_packaged_visual_permission(what, name, visual)
        except Exception:
            logger.exception(
                "Error on declaring permissions for packaged visuals in file %s", dirpath
            )
            if active_config.debug:
                raise


def available(
    what: VisualTypeName,
    all_visuals: dict[tuple[UserId, VisualName], TVisual],
) -> dict[VisualName, TVisual]:
    visuals: dict[VisualName, TVisual] = {}
    for visual_name, _visuals in available_by_owner(what, all_visuals).items():
        for user_id, visual in sorted(_visuals.items()):
            # Built-in
            if user_id == UserId.builtin():
                visuals[visual_name] = visual
            # Other users
            if user_id != UserId.builtin() and user_id != user.id:
                visuals[visual_name] = visual
            # Own
            if user.id == user_id:
                visuals[visual_name] = visual
    return visuals


# Get the list of visuals which are available to the user
# (which could be retrieved with get_visual)
def available_by_owner(
    what: VisualTypeName,
    all_visuals: dict[tuple[UserId, VisualName], TVisual],
) -> dict[VisualName, dict[UserId, TVisual]]:
    visuals: dict[VisualName, dict[UserId, TVisual]] = {}
    permprefix = what[:-1]

    def restricted_visual(visualname: VisualName) -> bool:
        permname = f"{permprefix}.{visualname}"
        return permname in permission_registry and not user.may(permname)

    def restricted_packaged_visual(visualname: VisualName) -> bool:
        permname = f"{permprefix}.{visualname}_packaged"
        return permname in permission_registry and not user.may(permname)

    # 1. user's own visuals, if allowed to edit visuals
    if user.may("general.edit_" + what):
        for (user_id, visual_name), visual in all_visuals.items():
            if user_id == user.id:
                visuals.setdefault(visual_name, {})
                visuals[visual_name][user_id] = visual

    # 2. visuals of special users allowed to globally override built-in visuals
    for (user_id, visual_name), visual in all_visuals.items():
        # Honor original permissions for the current user
        if (
            visual_name not in visuals
            and published_to_user(visual)
            and user_may(user_id, "general.force_" + what)
            and user.may("general.see_user_" + what)
            and not restricted_visual(visual_name)
        ):
            visuals.setdefault(visual_name, {})
            visuals[visual_name][user_id] = visual

    # 3. Built-in visuals, if allowed.
    for (user_id, visual_name), visual in all_visuals.items():
        if user_id == UserId.builtin() and user.may(f"{permprefix}.{visual_name}"):
            visuals.setdefault(visual_name, {})
            visuals[visual_name][user_id] = visual

    # 4. other users visuals, if public. Still make sure we honor permission
    #    for built-in visuals. Also the permission "general.see_user_visuals" is
    #    necessary.
    if user.may("general.see_user_" + what):
        for (user_id, visual_name), visual in all_visuals.items():
            # Is there a built-in visual with the same name? If yes, honor permissions.
            if (
                visual_name not in visuals
                and published_to_user(visual)
                and not restricted_visual(visual_name)
            ):
                visuals.setdefault(visual_name, {})
                visuals[visual_name][user_id] = visual

    # 5. packaged visuals
    if user.may("general.see_packaged_" + what):
        for (user_id, visual_name), visual in all_visuals.items():
            if visual_name in visuals:
                continue
            if not visual["packaged"]:
                continue
            if not restricted_packaged_visual(visual_name):
                visuals.setdefault(visual_name, {})
                visuals[visual_name][user_id] = visual

    return visuals


def published_to_user(visual: TVisual) -> bool:
    if visual["public"] is True:
        return True

    if isinstance(visual["public"], tuple):
        if visual["public"][0] == "contact_groups":
            user_groups = set([] if user.id is None else userdb.contactgroups_of_user(user.id))
            return bool(user_groups.intersection(visual["public"][1]))
        if visual["public"][0] == "sites":
            user_sites = set(user.authorized_sites().keys())
            return bool(user_sites.intersection(visual["public"][1]))

    return False


def get_permissioned_visual(
    item: str,
    owner: UserId | None,
    what: str,
    permitted_visuals: dict[str, TVisual],
    all_visuals: dict[tuple[UserId, str], TVisual],
) -> TVisual:
    if (
        owner is not None
        and owner != user.id  # Var is set from edit page and can be empty string for built-in
        and user.may(  # user has top priority, thus only change if other user
            "general.edit_foreign_%ss" % what
        )
    ):
        if visual := all_visuals.get((owner, item)):
            return visual
        # We don't raise on not found immediately and let it trickle down to default permitted
        # as a failsafe for report inheritance. In general it is OK for other cases, because the
        # priority should be inverse, first pick from permitted, then if edit_foreign permissions
        # are available get from other user. In reports it still happens that the inheritance view
        # is of the active user not of the "owner". Resolution of those piorities would need to be
        # fixed in visuals.available to support foreign users.

    if visual := permitted_visuals.get(item):
        return visual
    raise MKUserError(
        "%s_name" % what, _("The requested %s %s does not exist") % (what, escape(item))
    )
