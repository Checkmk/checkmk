/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * A geo coordinate as stored: six decimals place an object to about ten
 * centimetres, and a pointer cannot do better. The full double the map hands
 * out would only overflow the fields that edit it.
 */
export function roundCoordinate(degrees: number): number {
  return Math.round(degrees * 1e6) / 1e6
}
