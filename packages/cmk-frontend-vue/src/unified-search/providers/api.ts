/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { Api } from '@/lib/api-client'
import { inject, provide, type InjectionKey } from 'vue'

export const apiServiceProvider = Symbol() as InjectionKey<Api>

provide(apiServiceProvider, new Api())

export function getApiServiceProvider(): Api {
  const api = inject(apiServiceProvider)
  if (api === undefined) {
    throw Error('can only be used inside vue')
  }
  return api
}
