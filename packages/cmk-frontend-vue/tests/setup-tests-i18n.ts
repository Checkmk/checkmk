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

export default function usei18n() {
  function _t(msg: string, interp: Record<string, string | number>) {
    return interpolate(msg, interp)
  }

  function _tn(
    singular: string,
    plural: string,
    n: number,
    interp: Record<string, string | number>
  ) {
    return interpolate(n === 1 ? singular : plural, interp)
  }

  function _tp(_: string, msg: string, interp: Record<string, string | number>) {
    return interpolate(msg, interp)
  }

  function _tnp(
    _: string,
    singular: string,
    plural: string,
    n: number,
    interp: Record<string, string | number>
  ) {
    return interpolate(n === 1 ? singular : plural, interp)
  }

  return {
    _t,
    _tn,
    _tp,
    _tnp
  }
}
