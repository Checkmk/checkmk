/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

function interpolate(msg: string, interp: Record<string, string | number>): string {
  return msg.replace(/%\{\s*([\w]+)\s*\}/g, (_, key) =>
    interp[key] !== undefined ? String(interp[key]) : `%{${key}}`
  )
}

export function dummyT(msg: string, interp?: Record<string, string | number>) {
  return interp === undefined ? msg : interpolate(msg, interp)
}

export function dummyTn(
  singular: string,
  plural: string,
  n: number,
  interp?: Record<string, string | number>
) {
  const msg = n === 1 ? singular : plural
  return interp === undefined ? msg : interpolate(msg, interp)
}

export function dummyTp(_: string, msg: string, interp?: Record<string, string | number>) {
  return dummyT(msg, interp)
}

export function dummyTnp(
  _: string,
  singular: string,
  plural: string,
  n: number,
  interp?: Record<string, string | number>
) {
  return dummyTn(singular, plural, n, interp)
}
