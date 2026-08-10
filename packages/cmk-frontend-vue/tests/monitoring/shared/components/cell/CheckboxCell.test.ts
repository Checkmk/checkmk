/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { defineComponent, h } from 'vue'

import CheckboxCell from '@/monitoring/shared/components/cell/CheckboxCell.vue'

function mountCell(value: boolean, onUpdate: (value: boolean) => void = () => {}) {
  return render(
    defineComponent({
      render() {
        return h('table', [
          h('tbody', [
            h('tr', [
              h(CheckboxCell, {
                modelValue: value,
                ariaLabel: 'Select row',
                'onUpdate:modelValue': onUpdate
              })
            ])
          ])
        ])
      }
    })
  )
}

function hitArea(): HTMLElement {
  const element = document.querySelector('.monitoring-checkbox-cell__hit-area')
  if (element === null) {
    throw new Error('checkbox cell has no hit area')
  }
  return element as HTMLElement
}

test('renders the checkbox in the checked state', () => {
  mountCell(true)

  expect(screen.getByRole('checkbox', { name: 'Select row' })).toHaveAttribute(
    'aria-checked',
    'true'
  )
})

test('clicking the checkbox emits the toggled value', async () => {
  const onUpdate = vi.fn()
  mountCell(false, onUpdate)

  await userEvent.click(screen.getByRole('checkbox', { name: 'Select row' }))

  expect(onUpdate).toHaveBeenCalledWith(true)
})

test('activating the checkbox with the keyboard emits the toggled value once', async () => {
  const onUpdate = vi.fn()
  mountCell(false, onUpdate)

  screen.getByRole('checkbox', { name: 'Select row' }).focus()
  await userEvent.keyboard(' ')

  expect(onUpdate).toHaveBeenCalledTimes(1)
  expect(onUpdate).toHaveBeenCalledWith(true)
})

test('clicking the cell next to the checkbox selects it', async () => {
  const onUpdate = vi.fn()
  mountCell(false, onUpdate)

  await userEvent.click(hitArea())

  expect(onUpdate).toHaveBeenCalledWith(true)
})

test('clicking the cell next to a checked checkbox deselects it', async () => {
  const onUpdate = vi.fn()
  mountCell(true, onUpdate)

  await userEvent.click(hitArea())

  expect(onUpdate).toHaveBeenCalledWith(false)
})

test('the hit area spans the whole cell', () => {
  mountCell(false)

  const cell = document.querySelector('td.monitoring-checkbox-cell')

  expect(cell).toContainElement(hitArea())
  expect(hitArea().parentElement).toHaveClass('monitoring-base-cell__plain')
})
