/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

export enum RestrictedToSingle {
  NO = 'no',
  HOST = 'host',
  CUSTOM = 'custom'
}

export type ObjectType = string

export type DashboardShare = components['schemas']['DashboardShare']
