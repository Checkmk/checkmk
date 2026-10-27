#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Uploads SNMP MIBs: stores them as custom MIBs and compiles them for translating traps"""

import functools
import io
import re
import zipfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Protocol

import cmk.ec.export as ec  # astrein: disable=module-layers
from cmk.gui.i18n import _


class CompileMib(Protocol):
    """Compiles the MIB with the name and content into the destination directory

    The MIB may import the MIBs in the source directories and the compiled ones in the search
    directories. The result tells the status of the MIB and of the ones it imports."""

    def __call__(
        self,
        *,
        mibname: ec.MibName,
        content: str,
        source_dirs: Iterable[Path],
        search_dirs: Iterable[Path],
        destination_dir: Path,
    ) -> Mapping[ec.MibName, ec.MibStatus]: ...


def upload_mibs(
    filename: str,
    mimetype: str,
    content: bytes,
    *,
    make_compile_mib: Callable[[], CompileMib],
    paths: ec.Paths,
    source_dirs: Sequence[Path],
    on_stored: Callable[[str, str], None],
) -> str:
    """Compiles the MIB file, or the ones in the root directory of the zip file, and stores them

    The MIBs may import the ones in the source directories and the compiled ones. They are all
    compiled with the same compiling, made only when compiling the first one, as loading the
    compiler takes long. Right after storing a MIB file, on_stored gets its name and the message
    about it, and its failure fails the upload. The result is the message about all uploaded MIB
    files for the user."""
    make_compile_mib = functools.cache(make_compile_mib)
    _validate_mib_file_name(filename)

    if zipfile.is_zipfile(io.BytesIO(content)):
        return _upload_zip_file(
            content,
            make_compile_mib=make_compile_mib,
            paths=paths,
            source_dirs=source_dirs,
            on_stored=on_stored,
        )

    if (
        mimetype == "application/tar"
        or filename.lower().endswith(".gz")
        or filename.lower().endswith(".tgz")
    ):
        raise Exception(_("Sorry, uploading TAR/GZ files is not yet implemented."))

    msg = _upload_mib_file(
        filename, content, make_compile_mib=make_compile_mib, paths=paths, source_dirs=source_dirs
    )
    on_stored(filename, msg)
    return msg


def _upload_zip_file(
    content: bytes,
    *,
    make_compile_mib: Callable[[], CompileMib],
    paths: ec.Paths,
    source_dirs: Sequence[Path],
    on_stored: Callable[[str, str], None],
) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as zip_obj:
        messages = []
        success, fail = 0, 0
        for entry in zip_obj.infolist():
            mib_file_name = entry.filename
            try:
                if mib_file_name[-1] == "/":
                    continue  # silently skip directories
                _validate_mib_file_name(mib_file_name)
                with zip_obj.open(mib_file_name) as mib_obj:
                    msg = _upload_mib_file(
                        mib_file_name,
                        mib_obj.read(),
                        make_compile_mib=make_compile_mib,
                        paths=paths,
                        source_dirs=source_dirs,
                    )
            except Exception as e:
                messages.append(
                    _("Skipped %(mib_file_name)s: %(e)s") % {"mib_file_name": mib_file_name, "e": e}
                )
                fail += 1
            else:
                # The MIB file is stored, so it's no longer one to skip.
                on_stored(mib_file_name, msg)
                messages.append(msg)
                success += 1

    return "<br>\n".join(messages) + "<br><br>\nProcessed %d MIB files, skipped %d MIB files" % (
        success,
        fail,
    )


def _upload_mib_file(
    filename: str,
    content_bytes: bytes,
    *,
    make_compile_mib: Callable[[], CompileMib],
    paths: ec.Paths,
    source_dirs: Sequence[Path],
) -> str:
    # FIXME: This is a temporary local fix that should be removed once
    # handling of file contents uses a uniformly encoded representation
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = content_bytes.decode("latin-1")

    msg = _validate_and_compile_mib(
        mibname=_module_name(filename, content),
        content=content,
        make_compile_mib=make_compile_mib,
        paths=paths,
        source_dirs=source_dirs,
    )
    paths.local_mibs_dir.value.mkdir(parents=True, exist_ok=True)
    with (paths.local_mibs_dir.value / filename).open("wb") as f:
        f.write(content_bytes)
    return msg


# The definition of a MIB module starts with its name, e.g. "IF-MIB DEFINITIONS ::= BEGIN", which
# comments may precede and interrupt. Like for the compiler, they run from "--" to the end of the
# line, which "\r" may end, too.
_COMMENT = re.compile(r"--[^\r\n]*")
_MODULE_DEFINITION = re.compile(
    r"(?:^|(?<=[\r\n]))[ \t]*([A-Za-z][-A-Za-z0-9]*)\s+(?:\{[^}]*\}\s*)?DEFINITIONS\b"
)


def defined_module_name(lines: Iterable[str]) -> ec.MibName | None:
    """The name of the MIB module the lines of a MIB file define, if any

    The compiler names the compiled module like that. It reads the lines only up to the definition,
    which comes first apart from comments, so the MIB list needn't read whole files."""
    text = ""
    for line in lines:
        text += _COMMENT.sub("", line)
        if "DEFINITIONS" in line and (match := _MODULE_DEFINITION.search(text)):
            return ec.MibName(match.group(1))
    return None


def _module_name(filename: str, content: str) -> ec.MibName:
    """The name of the MIB module the content defines, by default the one of the file

    The compiler tells the status of a MIB by the name in its definition, which may differ from the
    one of its file, e.g. in case."""
    return defined_module_name(io.StringIO(content)) or ec.MibName(
        filename.split(".", maxsplit=1)[0].upper()
    )


def _validate_mib_file_name(filename: str) -> None:
    if filename.startswith(".") or "/" in filename:
        raise Exception(_("Invalid file name"))


def _validate_and_compile_mib(
    *,
    mibname: ec.MibName,
    content: str,
    make_compile_mib: Callable[[], CompileMib],
    paths: ec.Paths,
    source_dirs: Sequence[Path],
) -> str:
    if not content or content.isspace():
        raise Exception(_("The file is empty"))

    results = make_compile_mib()(
        mibname=mibname,
        content=content,
        source_dirs=source_dirs,
        search_dirs=[paths.compiled_mibs_dir.value],
        destination_dir=paths.compiled_mibs_dir.value,
    )
    errors = []
    for name, mib_status in sorted(results.items()):
        if mibname == name and mib_status.status == "failed":
            raise Exception(
                _("Failed to compile your module: %(error)s") % {"error": mib_status.error}
            )
        if mib_status.status == "missing":
            errors.append(_("%(name)s - Dependency missing") % {"name": name})
        elif mib_status.status == "failed":
            errors.append(
                _("%(name)s - Failed to compile (%(error)s)")
                % {"name": name, "error": mib_status.error}
            )
    msg = _("MIB file %(mibname)s uploaded.") % {"mibname": mibname}
    if errors:
        msg += "<br>" + _("But there were errors:") + "<br>"
        msg += "<br>\n".join(errors)
    return msg
