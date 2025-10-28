/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export type CmkStateName = 'Ok' | 'Warning' | 'Critical' | 'Unknown'

export enum CmkState {
  OK = 0,
  WARNING = 1,
  CRITICAL = 2,
  UNKNOWN = 3
}

export function mapCmkState(state: CmkState): CmkStateName {
  switch (state) {
    case CmkState.OK:
      return 'Ok'
    case CmkState.WARNING:
      return 'Warning'
    case CmkState.CRITICAL:
      return 'Critical'
    default:
      return 'Unknown'
  }
}
