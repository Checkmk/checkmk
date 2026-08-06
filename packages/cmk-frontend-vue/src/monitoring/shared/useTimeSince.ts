/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

/** Render how long ago a timestamp was, in the coarsest unit that still says something. */
export function useTimeSince(): (iso: string) => string {
  const { _t } = usei18n()

  return (iso: string): string => {
    const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000))
    if (seconds < 60) {
      return _t('%{count} sec', { count: seconds })
    }
    const minutes = Math.round(seconds / 60)
    if (minutes < 60) {
      return _t('%{count} min', { count: minutes })
    }
    const hours = Math.round(minutes / 60)
    if (hours < 24) {
      return _t('%{count} h', { count: hours })
    }
    return _t('%{count} d', { count: Math.round(hours / 24) })
  }
}
