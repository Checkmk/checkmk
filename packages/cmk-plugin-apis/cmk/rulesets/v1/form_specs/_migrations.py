#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, TypeVar
from uuid import uuid4

from ._levels import _PredictiveLevelsT, LevelDirection, LevelsConfigModel, SimpleLevelsConfigModel

_NumberT = TypeVar("_NumberT", int, float)


def _extract_bound(
    model: object, scale: float, ntype: type[_NumberT], level_dir: LevelDirection | None
) -> tuple[_NumberT, _NumberT] | None:
    match (model, level_dir):
        case ({"levels_upper_min": (warn, crit)}, LevelDirection.UPPER):
            return ntype(warn * scale), ntype(crit * scale)  # type: ignore[misc]
        case _:
            return None


def _extract_levels(
    raw_levels: (
        tuple[Literal["absolute"], tuple[int, int] | tuple[float, float]]
        | tuple[Literal["relative"], tuple[float, float]]
        | tuple[Literal["stdev"], tuple[float, float]]
    ),
    scale: float,
    ntype: type[_NumberT],
) -> (
    tuple[Literal["absolute"], tuple[_NumberT, _NumberT]]
    | tuple[Literal["relative"], tuple[float, float]]
    | tuple[Literal["stdev"], tuple[float, float]]
):
    match raw_levels:
        case ("absolute", (int(warn), int(crit)) | (float(warn), float(crit))):
            return "absolute", (ntype(warn * scale), ntype(crit * scale))
        case ("relative", (float(warn), float(crit))):
            return "relative", (warn, crit)
        case ("stdev", (float(warn), float(crit))):
            return "stdev", (float(warn), float(crit))
        case _:
            raise TypeError(f"Invalid predictive levels model {raw_levels}")


def _parse_to_predictive_levels(
    model: object, scale: float, ntype: type[_NumberT], level_dir: LevelDirection
) -> _PredictiveLevelsT[_NumberT] | None:
    match model:
        # already migrated
        # NOTE: Using a variable of type "type[...]" in a class pattern should be OK, but
        # mypy complains about that, see e.g. https://github.com/python/mypy/issues/17133.
        # As a consequence, we need those three suppressions below. :-/
        case {
            "period": "wday" | "day" | "hour" | "minute",
            "horizon": int(),
            "levels": ("absolute", (ntype(), ntype()))  # type: ignore[misc]
            | ("relative", (float(), float()))
            | ("stdev", (float(), float())),
            "bound": (ntype(), ntype()) | None,  # type: ignore[misc]
        }:
            return model  # type: ignore[return-value]
        # migrate upper predictive levels
        case {
            "period": "wday" | "day" | "hour" | "minute" as p,
            "horizon": int() as h,
            "levels_upper": ("absolute", (int(), int()) | (float(), float()))
            | ("relative", (float(), float()))
            | ("stdev", (float(), float())) as raw_levels,
        } if level_dir is LevelDirection.UPPER:
            return _PredictiveLevelsT[_NumberT](
                period=p,
                horizon=h,
                levels=_extract_levels(raw_levels, scale, ntype),  # type: ignore[misc]
                bound=_extract_bound(model, scale, ntype, level_dir),
            )
        # migrate lower predictive levels
        case {
            "period": "wday" | "day" | "hour" | "minute" as p,
            "horizon": int() as h,
            "levels_lower": ("absolute", (int(), int()) | (float(), float()))
            | ("relative", (float(), float()))
            | ("stdev", (float(), float())) as raw_levels,
        } if level_dir is LevelDirection.LOWER:
            return _PredictiveLevelsT[_NumberT](
                period=p,
                horizon=h,
                levels=_extract_levels(raw_levels, scale, ntype),  # type: ignore[misc]
                bound=_extract_bound(model, scale, ntype, level_dir),
            )
        # migrate not configured predictive levels
        case (
            {
                "period": "wday" | "day" | "hour" | "minute",
                "horizon": int(),
            } as val
        ) if "levels" not in val and "bound" not in val:  # type: ignore[operator]
            return None
        case _:
            raise TypeError(
                f"Could not migrate {model} of type {ntype.__name__} to a {type(model).__name__} "
                f"based Levels model"
            )


def _migrate_to_levels(
    model: object, scale: float, ntype: type[_NumberT], level_dir: LevelDirection
) -> LevelsConfigModel[_NumberT]:
    if (already_migrated := _parse_already_migrated(model, ntype, level_dir)) is not None:
        return already_migrated

    match model:
        case None | (None, None):
            return "no_levels", None

        case (int(warn), int(crit)) | (float(warn), float(crit)):
            return "fixed", (ntype(warn * scale), ntype(crit * scale))

        # 2.2. format + format released in 2.3.0b3
        case dict(val_dict) | ("predictive", dict(val_dict)):
            if (
                pred_levels := _parse_to_predictive_levels(val_dict, scale, ntype, level_dir)  # type: ignore[misc]
            ) is None:
                return "no_levels", None
            return "cmk_postprocessed", "predictive_levels", pred_levels

        case _:
            raise TypeError(
                f"Could not migrate {model} of type {ntype.__name__} to a {type(model).__name__} "
                f"based Levels model"
            )


def _parse_already_migrated(
    model: object, ntype: type[_NumberT], level_dir: LevelDirection
) -> LevelsConfigModel[_NumberT] | None:
    match model:
        case ("no_levels", None):
            return "no_levels", None

        case ("fixed", (int(w), int(c)) | (float(w), float(c))):
            return "fixed", (ntype(w), ntype(c))

        case ("cmk_postprocessed", "predictive_levels", val_dict):
            # do not scale, but for the typing we still need to parse.
            if (
                pred_levels := _parse_to_predictive_levels(val_dict, 1.0, ntype, level_dir)
            ) is None:
                return "no_levels", None
            return "cmk_postprocessed", "predictive_levels", pred_levels
    return None


def migrate_to_upper_integer_levels(model: object, scale: float = 1.0) -> LevelsConfigModel[int]:
    """
    Transform a previous levels configuration (Tuple, SimpleLevels, Levels or PredictiveLevels)
    representing upper (warn, crit) levels to an integer-based model of the `Levels` FormSpec.
    The decimal part of floating point values will be truncated when converting to integer values.

    Args:
        model: Old value presented to the consumers to be migrated
        scale: Factor to scale the levels with.
            For example, a scale of 1000 would convert milliseconds to seconds.
    """
    return _migrate_to_levels(model, scale, int, LevelDirection.UPPER)


def migrate_to_upper_float_levels(model: object, scale: float = 1.0) -> LevelsConfigModel[float]:
    """
    Transform a previous levels configuration (Tuple, SimpleLevels, Levels or PredictiveLevels)
    representing upper (warn, crit) levels to a float-based model of the `Levels` FormSpec

    Args:
        model: Old value presented to the consumers to be migrated
        scale: Factor to scale the levels with.
            For example, a scale of 1000 would convert milliseconds to seconds.
    """
    return _migrate_to_levels(model, scale, float, LevelDirection.UPPER)


def migrate_to_lower_integer_levels(model: object, scale: float = 1.0) -> LevelsConfigModel[int]:
    """
    Transform a previous levels configuration (Tuple, SimpleLevels, Levels or PredictiveLevels)
    representing lower (warn, crit) levels to an integer-based model of the `Levels` FormSpec.
    The decimal part of floating point values will be truncated when converting to integer values.

    Args:
        model: Old value presented to the consumers to be migrated
        scale: Factor to scale the levels with.
            For example, a scale of 1000 would convert milliseconds to seconds.
    """
    return _migrate_to_levels(model, scale, int, LevelDirection.LOWER)


def migrate_to_lower_float_levels(model: object, scale: float = 1.0) -> LevelsConfigModel[float]:
    """
    Transform a previous levels configuration (Tuple, SimpleLevels, Levels or PredictiveLevels)
    representing lower (warn, crit) levels to a float-based model of the `Levels` FormSpec

    Args:
        model: Old value presented to the consumers to be migrated
        scale: Factor to scale the levels with.
            For example, a scale of 1000 would convert milliseconds to seconds.
    """
    return _migrate_to_levels(model, scale, float, LevelDirection.LOWER)


def _migrate_to_simple_levels(
    model: object, scale: float, ntype: type[_NumberT]
) -> SimpleLevelsConfigModel[_NumberT]:
    match model:
        case None | (None, None) | ("no_levels", None):
            return "no_levels", None

        case ("fixed", (int(warn), int(crit)) | (float(warn), float(crit))):
            return "fixed", (ntype(warn), ntype(crit))

        case (int(warn), int(crit)) | (float(warn), float(crit)):
            return "fixed", (ntype(warn * scale), ntype(crit * scale))

        case ("cmk_postprocessed", "predictive_levels", val_dict) | val_dict if isinstance(
            val_dict, dict
        ):
            raise TypeError(
                f"Could not migrate {model!r} to SimpleLevelsConfigModel. "
                "Consider using Levels instead of SimpleLevels."
            )
        case _:
            raise TypeError(f"Could not migrate {model!r} to SimpleLevelsConfigModel.")


def migrate_to_integer_simple_levels(
    model: object, scale: float = 1.0
) -> SimpleLevelsConfigModel[int]:
    """
    Transform a previous levels configuration (Tuple or SimpleLevels)
    representing (warn, crit) levels to an integer-based model of the `SimpleLevels` FormSpec.
    The decimal part of floating point values will be truncated when converting to integer values.

    Args:
        model: Old value presented to the consumers to be migrated
        scale: Factor to scale the levels with.
            For example, a scale of 1000 would convert milliseconds to seconds.
    """
    return _migrate_to_simple_levels(model, scale, int)


def migrate_to_float_simple_levels(
    model: object, scale: float = 1.0
) -> SimpleLevelsConfigModel[float]:
    """
    Transform a previous levels configuration (Tuple or SimpleLevels)
    representing (warn, crit) levels to a float-based model of the `SimpleLevels` FormSpec

    Args:
        model: Old value presented to the consumers to be migrated
    """
    return _migrate_to_simple_levels(model, scale, float)


def migrate_to_password(
    model: object,
) -> tuple[
    Literal["cmk_postprocessed"], Literal["explicit_password", "stored_password"], tuple[str, str]
]:
    """
    Transform a previous password configuration represented by ("password", <password>) or
    ("store", <password-store-id>) to a model of the `Password` FormSpec, represented by
    ("cmk_postprocessed", "explicit_password", (<password-id>, <password>)) or
    ("cmk_postprocessed", "stored_password", (<password-store-id>, "")).

    Args:
        model: Old value presented to the consumers to be migrated
    """
    match model:
        # old password format
        case "password", str(password):
            return (
                "cmk_postprocessed",
                "explicit_password",
                (str(uuid4()), password),
            )
        case "store", str(password_store_id):
            return "cmk_postprocessed", "stored_password", (password_store_id, "")

        # password format released in 2.3.0 beta
        case "explicit_password", str(password_id), str(password):
            return "cmk_postprocessed", "explicit_password", (password_id, password)
        case "stored_password", str(password_store_id), str(password):
            return "cmk_postprocessed", "stored_password", (password_store_id, password)

        # already migrated passwords
        case "cmk_postprocessed", "explicit_password", (str(password_id), str(password)):
            return "cmk_postprocessed", "explicit_password", (password_id, password)
        case "cmk_postprocessed", "stored_password", (str(password_store_id), str(password)):
            return "cmk_postprocessed", "stored_password", (password_store_id, password)

    raise TypeError(f"Could not migrate {model!r} to Password.")


def migrate_to_proxy(
    model: object,
) -> tuple[
    Literal["cmk_postprocessed"],
    Literal["environment_proxy", "no_proxy", "stored_proxy", "explicit_proxy"],
    str,
]:
    """
    Transform a previous proxy configuration to a model of the `Proxy` FormSpec.
    Previous configurations are transformed in the following way:

        ("global", <stored-proxy-id>) -> ("cmk_postprocessed", "stored_proxy", <stored-proxy-id>)
        ("environment", "environment") -> ("cmk_postprocessed", "environment_proxy", "")
        ("url", <url>) -> ("cmk_postprocessed", "explicit_proxy", <url>)
        ("no_proxy", None) -> ("cmk_postprocessed", "no_proxy", "")

    Args:
        model: Old value presented to the consumers to be migrated
    """
    match model:
        case "global", str(stored_proxy_id):
            return "cmk_postprocessed", "stored_proxy", stored_proxy_id
        case "environment", "environment":
            return "cmk_postprocessed", "environment_proxy", ""
        case "url", str(url):
            return "cmk_postprocessed", "explicit_proxy", url
        case "no_proxy", None:
            return "cmk_postprocessed", "no_proxy", ""
        case "cmk_postprocessed", "stored_proxy", str(stored_proxy_id):
            return "cmk_postprocessed", "stored_proxy", stored_proxy_id
        case "cmk_postprocessed", "environment_proxy", str():
            return "cmk_postprocessed", "environment_proxy", ""
        case "cmk_postprocessed", "explicit_proxy", str(url):
            return "cmk_postprocessed", "explicit_proxy", url
        case "cmk_postprocessed", "no_proxy", str():
            return "cmk_postprocessed", "no_proxy", ""

    raise TypeError(f"Could not migrate {model!r} to Proxy.")


def migrate_to_time_period(
    model: object,
) -> tuple[Literal["cmk_postprocessed"], Literal["stored_time_period"], str]:
    """
    Transform a previous time period configuration to a model of the `TimePeriod` FormSpec.
    Previous configurations are transformed in the following way:

        <time-period> -> ("time_period", "preconfigured", <time-period>)

    Args:
        model: Old value presented to the consumers to be migrated
    """
    match model:
        case str(time_period):
            return "cmk_postprocessed", "stored_time_period", time_period
        case "cmk_postprocessed", "stored_time_period", str(time_period):
            return "cmk_postprocessed", "stored_time_period", time_period

    raise TypeError(f"Could not migrate {model!r} to TimePeriod.")
