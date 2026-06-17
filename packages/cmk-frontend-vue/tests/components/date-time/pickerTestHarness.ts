/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { type Component, defineComponent, h, ref, shallowRef } from 'vue'

type UserEvent = ReturnType<typeof userEvent.setup>

export type ModelPickerView<ModelValue> = ReturnType<typeof render> & {
  /** Every value the picker has emitted via `update:modelValue`, in order. */
  updates: ModelValue[]
  /** The host's current model value (kept in sync with `update:modelValue`). */
  currentModel: () => ModelValue
  /** Every `update:open` the picker has emitted, in order. */
  openLog: boolean[]
  /** The host's current open state. */
  currentOpen: () => boolean
}

export function lastValue<T>(values: readonly T[], label = 'value'): T {
  const value = values.at(-1)
  if (value === undefined) {
    throw new Error(`Missing ${label}`)
  }
  return value
}

/**
 * Open the real `CmkDropdown` whose accessible name is `label` (its `label` prop), revealing its
 * options. `index` selects among several dropdowns sharing a label (e.g. the per-grid "Month" /
 * "Year" dropdowns when a calendar shows multiple grids).
 */
export async function openDropdown(user: UserEvent, label: string, index = 0): Promise<void> {
  const combobox = screen.getAllByRole('combobox', { name: label })[index]!
  await user.click(combobox)
}

/** Open the `CmkDropdown` named `label` (see {@link openDropdown}) and click the option `optionLabel`. */
export async function selectDropdownOption(
  user: UserEvent,
  label: string,
  optionLabel: string,
  index = 0
): Promise<void> {
  await openDropdown(user, label, index)
  await user.click(await screen.findByRole('option', { name: optionLabel }))
}

/**
 * Render a `v-model`-driven picker through a tiny host that keeps both `modelValue` and `open`
 * self-tracked, so committed writes and open/close transitions are observable from the outside —
 * the way a real consumer sees them. Tests then drive the picker only through its accessible
 * surface (roles + names) and assert on `updates` / `currentModel` / `openLog`.
 */
export function renderModelPicker<ModelValue>(
  component: Component,
  initialModel: ModelValue,
  props: Record<string, unknown> = {},
  slots: Record<string, (...args: never[]) => unknown> = {}
): ModelPickerView<ModelValue> {
  const model = shallowRef<ModelValue>(initialModel)
  const open = ref(false)
  const updates: ModelValue[] = []
  const openLog: boolean[] = []
  const view = render(
    defineComponent({
      setup() {
        return () =>
          h(
            component,
            {
              modelValue: model.value,
              open: open.value,
              ...props,
              'onUpdate:modelValue': (value: ModelValue) => {
                model.value = value
                updates.push(value)
              },
              'onUpdate:open': (value: boolean) => {
                open.value = value
                openLog.push(value)
              }
            },
            slots
          )
      }
    })
  )

  return {
    ...view,
    updates,
    currentModel: () => model.value,
    openLog,
    currentOpen: () => open.value
  }
}
