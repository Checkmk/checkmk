/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { InjectionKey } from 'vue'

import type { FilterHTTPVars } from './widget.ts'

export const urlParamsKey: InjectionKey<FilterHTTPVars> = Symbol('urlParams')

/** Opens the network flow host detail slide-in for the given IP address. */
export type OpenHostSlideIn = (ip: string) => void
export const hostSlideInKey: InjectionKey<OpenHostSlideIn> = Symbol('networkFlowHostSlideIn')
