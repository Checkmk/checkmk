#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""This is a capsule for python pillow aka PIL"""

from __future__ import annotations

import enum
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from typing import NamedTuple

from PIL import (
    Image,
    PngImagePlugin,
    UnidentifiedImageError,
)


class ImageSize(NamedTuple):
    width: int
    height: int


class BoundingBox(NamedTuple):
    left: int
    upper: int
    right: int
    lower: int


class ImageType(enum.Enum):
    PNG = "PNG"
    JPG = "JPEG"


class CMKImage:
    """An image

    Some thoughts on performance:
    We currently hold the image in memory since we do not know what we want with that later. Images
    are usually not that big, a 10MB image can be considered huge and RAM wise small so let's go
    with that for now."""

    def __init__(self, bytes_: bytes, image_types: ImageType | Iterable[ImageType]) -> None:
        self._types = (image_types,) if isinstance(image_types, ImageType) else image_types

        try:
            self._pil = Image.open(
                BytesIO(bytes_), formats=[image_type.value for image_type in self._types]
            )
        except UnidentifiedImageError as exception:
            raise ValueError("Image type not supported") from exception

        self._metadata: dict[str, str] | None = None

    def image_size(self) -> ImageSize:
        return ImageSize(self._pil.width, self._pil.height)

    def get_comment(self) -> str | None:
        return self._pil.info.get("Comment")

    def add_metadata(self, key: str, value: str) -> None:
        if self._metadata is None:
            self._metadata = {}
        self._metadata[key] = value

    @classmethod
    def from_path(cls, path: Path, image_types: ImageType | Iterable[ImageType]) -> CMKImage:
        return cls(path.read_bytes(), image_types)

    def pil(self) -> Image.Image:
        return self._pil

    def get_bounding_box(self) -> BoundingBox:
        bbox = self._pil.getbbox()
        if bbox is None:
            raise ValueError("Image is empty")
        return BoundingBox(*bbox)

    def save(self, path: Path, image_type: ImageType) -> None:
        if image_type is ImageType.PNG:
            meta: PngImagePlugin.PngInfo | None = None
            if self._metadata:
                meta = PngImagePlugin.PngInfo()
                for key, value in self.pil().info.items():
                    if isinstance(value, bytes | str):
                        meta.add_text(key, value, False)

                for key, value in self._metadata.items():
                    meta.add_text(key, value, False)

            self._pil.save(path, "PNG", pnginfo=meta)
            return

        raise NotImplementedError("Only PNG is supported at the moment")
