#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Reading a NagVis installation's maps, images and rotation pools as Maps data.

See "Update from NagVis" in ``doc/documentation/arch-comp-maps.rst`` for the files
read. None of them is changed here.
"""

import re
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import cmk.utils.paths
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.gui.exceptions import MKUserError
from cmk.maps.gui._cfg_import import decode_cfg, parse_cfg_upload
from cmk.maps.gui._image_security import (
    ICON_SUFFIXES,
    is_valid_image,
    is_valid_image_name,
    safe_image_stem,
)
from cmk.maps.gui._images import delete_image, icon_name_for, import_background, store_icon
from cmk.maps.shared.map_payload import MapPayload
from cmk.maps.shared.validators import is_valid_map_name

# How long Maps shows a map of a pool that has no interval of its own
# (``POOL_INTERVAL`` in useMapRotation.ts).
POOL_INTERVAL = 60

# NagVis' own pattern for a pool entry: an optional ``label:``, then a map name or
# a ``[URL]``.
_POOL_ENTRY_RE = re.compile(r"^(?:[^\[.]+:)?(?:\[(.+)\]|(.+))$")


def _nagvis_cfg_dir() -> Path:
    return cmk.utils.paths.omd_root / "etc" / "nagvis"


def nagvis_maps_dir() -> Path:
    return _nagvis_cfg_dir() / "maps"


@dataclass(frozen=True)
class RotationPool:
    interval: int
    maps: frozenset[str]
    urls: tuple[str, ...]


@dataclass(frozen=True)
class NagVisConfig:
    pools: dict[str, RotationPool]
    # Whether NagVis grants access by the Checkmk roles and contact groups, as on
    # every site unless its authorisation module was changed.
    checkmk_permissions: bool


def read_nagvis_config() -> NagVisConfig:
    """What the migration needs of NagVis' main configuration.

    NagVis reads ``conf.d`` first and ``nagvis.ini.php`` last; a later file adds to a
    section of an earlier one and overrides its keys.
    """
    cfg_dir = _nagvis_cfg_dir()
    sections: dict[str, dict[str, str]] = {}
    for path in [*sorted((cfg_dir / "conf.d").glob("*.ini.php")), cfg_dir / "nagvis.ini.php"]:
        with suppress(OSError):
            _read_ini(decode_cfg(path.read_bytes()), sections)
    general = sections.get("global", {})
    return NagVisConfig(
        pools=_rotation_pools(sections, _seconds(general.get("refreshtime")) or POOL_INTERVAL),
        checkmk_permissions=general.get("authorisationmodule") == "CoreAuthorisationModMultisite",
    )


def _rotation_pools(
    sections: Mapping[str, Mapping[str, str]], refresh_time: int
) -> dict[str, RotationPool]:
    pools: dict[str, RotationPool] = {}
    for section, options in sections.items():
        if not section.startswith("rotation_"):
            continue
        maps: set[str] = set()
        urls: list[str] = []
        for entry in options.get("maps", "").split(","):
            if not (match := _POOL_ENTRY_RE.match(entry.strip())):
                continue
            if match[1]:
                urls.append(match[1])
            else:
                maps.add(match[2].strip())
        pools[section.removeprefix("rotation_")] = RotationPool(
            # NagVis rotates a pool without an interval at its refresh time.
            interval=_seconds(options.get("interval")) or refresh_time,
            maps=frozenset(maps),
            urls=tuple(urls),
        )
    return pools


def _seconds(value: str | None) -> int | None:
    return int(value) if value and value.isdigit() and int(value) > 0 else None


def _read_ini(text: str, sections: dict[str, dict[str, str]]) -> None:
    section: dict[str, str] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = sections.setdefault(line[1:-1].strip(), {})
        elif section is not None and "=" in line:
            key, _sep, value = line.partition("=")
            value = value.strip()
            if len(value) > 1 and value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            section[key.strip().lower()] = value


def read_nagvis_map(path: Path, name: str, config: NagVisConfig) -> tuple[MapPayload, list[str]]:
    """The map in ``path`` as a map named ``name``, with what it lost on the way."""
    map_cfg, warnings = parse_cfg_upload(path.name, path.read_bytes())
    map_cfg["name"] = name
    warnings += _apply_rotation(map_cfg, path.stem, config.pools)
    if map_cfg["view"]["type"] == "worldmap":
        warnings.append("Its objects are kept outside the map file and are not migrated.")
    return map_cfg, warnings


def _apply_rotation(
    map_cfg: MapPayload, nagvis_name: str, pools: Mapping[str, RotationPool]
) -> list[str]:
    """Let the map take part in the NagVis rotation pools that list it."""
    names = sorted(pool for pool, spec in pools.items() if nagvis_name in spec.maps)
    usable = [pool for pool in names if is_valid_map_name(pool)]
    warnings = []
    if unusable := [pool for pool in names if not is_valid_map_name(pool)]:
        warnings.append(
            f"It is not added to the rotation pool(s) {', '.join(unusable)}, as Maps "
            "allows only letters, digits, underscores and hyphens in a pool name."
        )
    map_cfg["rotation_pools"] = usable
    intervals = sorted({pools[pool].interval for pool in usable})
    if not intervals:
        return warnings
    if len(intervals) > 1:
        warnings.append(
            f"NagVis shows it for {', '.join(map(str, intervals))} seconds in its "
            f"different rotation pools. Maps shows it for {intervals[0]} seconds in each."
        )
    if intervals[0] != POOL_INTERVAL:
        map_cfg["rotation_interval"] = intervals[0]
    return warnings


def _nagvis_image(kind: Literal["maps", "shapes"], ref: str) -> bytes | None:
    if not is_valid_image_name(ref):
        return None
    for htdocs in ("local/share/nagvis/htdocs", "share/nagvis/htdocs"):
        with suppress(OSError):
            return (
                cmk.utils.paths.omd_root / htdocs / "userfiles" / "images" / kind / ref
            ).read_bytes()
    return None


def copy_nagvis_background(map_cfg: MapPayload, owner: UserId) -> list[str]:
    """Store the map's NagVis background as its background in Maps."""
    if not (ref := map_cfg.get("background_image")):
        return []
    if (contents := _nagvis_image("maps", ref)) is not None and (
        stored := import_background(owner, map_cfg["name"], ref, contents)
    ):
        map_cfg["background_image"] = stored
        return []
    return [
        (
            f"The background {ref} is missing, unreadable or not a supported image. "
            "The map keeps the reference without the image."
        )
    ]


@dataclass
class ShapeCopies:
    """The shapes of a run's maps: named in Maps' image library first, added later.

    A map refers to a shape by the name it gets there, so the name is settled while
    the maps are prepared, and the file added once they are.
    """

    # The name each NagVis shape gets, ``None`` for one Maps cannot take.
    names: dict[str, str | None] = field(default_factory=dict)
    # The contents to add, by name.
    contents: dict[str, bytes] = field(default_factory=dict)
    # The names of the shapes the migrated maps show.
    used: set[str] = field(default_factory=set)
    # The names ``store`` added files under, not there before.
    added: list[str] = field(default_factory=list)

    def plan(self, map_cfg: MapPayload) -> tuple[set[str], list[str]]:
        """Point the map at its shapes' names; returns these names and the warnings."""
        used: set[str] = set()
        gifs: set[str] = set()
        missing: set[str] = set()
        for obj in map_cfg["objects"]:
            if obj["type"] != "image" or not (ref := obj.get("image_src")):
                continue
            if ref not in self.names:
                self.names[ref] = self._name(ref)
            if (name := self.names[ref]) is not None:
                obj["image_src"] = name
                used.add(name)
            elif Path(ref).suffix.lower() == ".gif":
                gifs.add(ref)
            else:
                missing.add(ref)
        warnings = []
        if gifs:
            warnings.append(
                f"The shape(s) {', '.join(sorted(gifs))} are GIF images, which Maps does not "
                "take as images. Convert them to PNG and upload them in the image library."
            )
        if missing:
            warnings.append(
                f"The shape(s) {', '.join(sorted(missing))} are missing, unreadable or not a "
                "supported image. They show as missing images."
            )
        return used, warnings

    def _name(self, ref: str) -> str | None:
        suffix = Path(ref).suffix.lower()
        contents = _nagvis_image("shapes", ref)
        if (
            contents is None
            or suffix not in ICON_SUFFIXES
            or not is_valid_image(contents, allow_gif=False)
        ):
            return None
        name = icon_name_for(safe_image_stem(ref) + suffix, contents, self.contents)
        self.contents[name] = contents
        return name

    def store(self) -> list[str]:
        """Add the shapes the migrated maps show; returns a warning for each that failed."""
        warnings = []
        for name in sorted(self.used):
            try:
                if store_icon(name, self.contents[name]):
                    self.added.append(name)
            except (OSError, MKGeneralException) as exc:
                warnings.append(
                    f"The shape {name} could not be added to the image library: {exc}. "
                    "The maps show it as a missing image."
                )
        return warnings

    def remove_added(self) -> None:
        for name in self.added:
            with suppress(OSError, MKUserError):
                delete_image(name, force=True)
