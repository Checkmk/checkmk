#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, TypeVar

from ._levels import _PredictiveLevelsT, LevelDirection, LevelsConfigModel, SimpleLevelsConfigModel

_NumberT = TypeVar("_NumberT", int, float)


def _extract_bound(
    model: object, scale: float, ntype: type[_NumberT], level_dir: LevelDirection | None
) -> tuple[_NumberT, _NumberT] | None:
    match (model, level_dir):
        case ({"levels_upper_min": (warn, crit)}, LevelDirection.UPPER):
            return ntype(warn * scale), ntype(crit * scale)
        case _:
            return None


def _extract_levels(
    raw_levels: tuple[Literal["absolute"], tuple[int, int] | tuple[float, float]]
    | tuple[Literal["relative"], tuple[float, float]]
    | tuple[Literal["stdev"], tuple[float, float]],
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
        case {
            "period": "wday" | "day" | "hour" | "minute",
            "horizon": int(),
            "levels": ("absolute", (ntype(), ntype()))
            | ("relative", (float(), float()))
            | ("stdev", (float(), float())),
            "bound": (ntype(), ntype()) | None,
        }:
            return model
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
                levels=_extract_levels(raw_levels, scale, ntype),
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
                levels=_extract_levels(raw_levels, scale, ntype),
                bound=_extract_bound(model, scale, ntype, level_dir),
            )
        # migrate not configured predictive levels
        case {
            "period": "wday" | "day" | "hour" | "minute",
            "horizon": int(),
        } as val if "levels" not in val and "bound" not in val:  # type: ignore[operator]
            return None
        case _:
            raise TypeError(
                f"Could not migrate {model} of type {ntype.__name__} to a {type(model).__name__} "
                f"based Levels model"
            )


def _migrate_to_levels(
    model: object, scale: float, ntype: type[_NumberT], level_dir: LevelDirection
) -> LevelsConfigModel[_NumberT]:
    match model:
        case None | (None, None) | ("no_levels", None):
            return "no_levels", None

        case ("fixed", (int(warn), int(crit)) | (float(warn), float(crit))) | (
            int(warn),
            int(crit),
        ) | (float(warn), float(crit)):
            return "fixed", (ntype(warn * scale), ntype(crit * scale))

        case ("predictive", val_dict) | val_dict if isinstance(val_dict, dict):
            if (
                pred_levels := _parse_to_predictive_levels(val_dict, scale, ntype, level_dir)
            ) is None:
                return "no_levels", None
            return "predictive", pred_levels

        case _:
            raise TypeError(
                f"Could not migrate {model} of type {ntype.__name__} to a {type(model).__name__} "
                f"based Levels model"
            )


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

        case ("fixed", (int(warn), int(crit)) | (float(warn), float(crit))) | (
            int(warn),
            int(crit),
        ) | (float(warn), float(crit)):
            return "fixed", (ntype(warn * scale), ntype(crit * scale))

        case ("predictive", val_dict) | val_dict if isinstance(val_dict, dict):
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
