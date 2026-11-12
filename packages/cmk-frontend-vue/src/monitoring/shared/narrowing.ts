/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { inject } from 'vue'

import {
  AFTER_NARROW,
  MONITORING_SERVICE,
  NARROW_TARGET
} from '@/monitoring/shared/components/MonitoringTableContext'
import {
  type ItemAction,
  type LabelCellItem,
  labelItemText
} from '@/monitoring/shared/components/cell/labelCellItem'
import type {
  ColumnCondition,
  MonitoringService
} from '@/monitoring/shared/services/MonitoringService'

/**
 * What a click on an entry narrows to, for the context it is shown in: the listing behind it,
 * or the page NARROW_TARGET names. Built in a component's setup, from what is provided there.
 */
export class Narrowing {
  constructor(
    private readonly service: MonitoringService<unknown> | null,
    private readonly afterNarrow: (() => void) | null,
    private readonly target: ((condition: ColumnCondition) => string) | null
  ) {}

  static inject(): Narrowing {
    return new Narrowing(
      inject(MONITORING_SERVICE, null),
      inject(AFTER_NARROW, null),
      inject(NARROW_TARGET, null)
    )
  }

  /** How entries narrowing to `conditionOf` act on a click; undefined where nothing can be narrowed. */
  actionFor(conditionOf: (item: LabelCellItem) => ColumnCondition): ItemAction | undefined {
    const { _t } = usei18n()
    const target = this.target
    if (target !== null) {
      return {
        title: (item) => _t('Show hosts with %{entry}', { entry: labelItemText(item) }),
        href: (item) => target(conditionOf(item))
      }
    }
    if (this.service === null) {
      return undefined
    }
    return { title: (item) => _t('Filter by %{entry}', { entry: labelItemText(item) }) }
  }

  narrow(condition: ColumnCondition): void {
    if (this.target !== null || this.service === null) {
      return
    }
    this.service.showOnly(condition)
    this.afterNarrow?.()
  }
}
