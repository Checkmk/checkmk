/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { type ComputedRef, computed, ref, watchEffect } from 'vue'

import type { CustomIcon } from '@/monitoring/shared/api/types'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionButtons.vue'
import { customIconSpec } from '@/monitoring/shared/components/customIcon'
import { ACTIONS_COLUMN_ID, ACTIONS_HEADER_WIDTH } from '@/monitoring/shared/constants'
import { columnId } from '@/monitoring/shared/tableState/schema'

/** A row that may carry custom icons, some of them actions. */
export interface RowWithCustomIcons {
  custom_icons?: readonly CustomIcon[] | null | undefined
}

const ACTION_BUTTON_WIDTH = 25
const ACTIONS_MENU_WIDTH = 50

/** The width of an Actions column with `buttons` inline buttons beside its action menu,
 * at least wide enough for its header. */
export function actionsColumnWidth(buttons: number): number {
  return Math.max(ACTIONS_HEADER_WIDTH, ACTIONS_MENU_WIDTH + buttons * ACTION_BUTTON_WIDTH)
}

/** How many custom actions a row shows beside its own; the rest go to its action menu. */
export const MAX_INLINE_CUSTOM_ACTIONS = 2

/** The custom icons of a row that carry an action, as actions of its Actions column. */
export const customActions = (icons: readonly CustomIcon[] | undefined): CellAction[] =>
  (icons ?? []).flatMap((icon) =>
    icon.url === undefined
      ? []
      : [
          {
            id: `custom-${icon.ident}`,
            label: untranslated(icon.title),
            icon: customIconSpec(icon),
            url: icon.url,
            // An action without a target opens in the frame it is clicked in, as in the views.
            target: icon.target ?? '_self'
          }
        ]
  )

/**
 * The actions of a row with its custom ones in front: the first few inline, left of its own,
 * the rest at the top of its action menu.
 */
export function withCustomActions(
  own: CellAction[],
  custom: CellAction[]
): { actions: CellAction[]; maxVisible: number } {
  const inline = custom.slice(0, MAX_INLINE_CUSTOM_ACTIONS)
  return {
    actions: [...inline, ...own, ...custom.slice(MAX_INLINE_CUSTOM_ACTIONS)],
    maxVisible: inline.length + own.length
  }
}

/**
 * The most custom actions a row of the listing has shown inline since the page loaded: the
 * Actions column widens for them, but does not shrink on a refresh, so it does not jump.
 */
export function useInlineCustomActionCount(
  rows: () => readonly RowWithCustomIcons[]
): ComputedRef<number> {
  const most = ref(0)
  watchEffect(() => {
    most.value = Math.max(
      most.value,
      ...rows().map((row) =>
        Math.min(MAX_INLINE_CUSTOM_ACTIONS, customActions(row.custom_icons ?? undefined).length)
      )
    )
  })
  return computed(() => most.value)
}

/** The Actions column widened by the room `inline` custom actions take beside a row's own. */
export function sizeActionsColumn<T>(columns: ColumnDef<T>[], inline: number): ColumnDef<T>[] {
  const extra = inline * ACTION_BUTTON_WIDTH
  return columns.map((column) =>
    columnId(column) === ACTIONS_COLUMN_ID && extra > 0
      ? {
          ...column,
          minSize: (column.minSize ?? 0) + extra,
          maxSize: (column.maxSize ?? column.minSize ?? 0) + extra
        }
      : column
  )
}
