/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { inject } from 'vue'
import type { InjectionKey } from 'vue'

interface GetWidget {
  (widgetType: string): unknown
}

export const quickSetupGetWidgetKey = Symbol() as InjectionKey<GetWidget>

export function getGetWidget(): GetWidget {
  const getWidget = inject(quickSetupGetWidgetKey)
  if (getWidget === undefined) {
    throw Error('can only be used inside quick setup context')
  }
  return getWidget
}
