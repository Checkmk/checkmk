/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import CmkFlyout from 'cmk-ui-library/components/CmkFlyout'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { afterEach } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import MonitoringTableRow from '@/monitoring/shared/components/MonitoringTableRow.vue'
import BaseCell from '@/monitoring/shared/components/cell/BaseCell.vue'
import FilterDropdown from '@/monitoring/shared/components/filter/FilterDropdown.vue'

import { markText, pastDoubleClick, userOnFakeClock } from '../deferredClick'

afterEach(() => {
  vi.restoreAllMocks()
})

type Popup = 'filter' | 'flyout'

function mountRow(
  props: { clickable?: boolean; onOpen?: () => void },
  popup?: Popup,
  onOpenDetails: () => void = () => {}
) {
  const flyoutOpen = ref(false)
  return render(
    defineComponent({
      render() {
        return h('div', [
          popup === 'flyout'
            ? h(
                CmkFlyout,
                {
                  open: flyoutOpen.value,
                  label: untranslated('Range'),
                  restoreFocus: () => {},
                  onCancel: () => {
                    flyoutOpen.value = false
                  }
                },
                {
                  trigger: () =>
                    h(
                      'button',
                      {
                        type: 'button',
                        onClick: () => {
                          flyoutOpen.value = !flyoutOpen.value
                        }
                      },
                      'Open flyout'
                    ),
                  default: () => 'flyout content'
                }
              )
            : null,
          popup === 'filter'
            ? h(
                FilterDropdown,
                { definition: { type: 'string-input', field: 'name' }, label: 'Name' },
                {
                  trigger: ({ toggle }: { toggle: () => void }) =>
                    h('button', { type: 'button', onClick: toggle }, 'Open filter')
                }
              )
            : null,
          h('table', [
            h('tbody', [
              h(MonitoringTableRow, props, () => [
                h('td', 'plain text'),
                h(BaseCell, { interactive: true }, () => 'chip area'),
                h(BaseCell, { button: true, onClick: onOpenDetails }, () => 'button cell'),
                h('td', [h('a', { href: '#' }, 'a link')])
              ])
            ])
          ])
        ])
      }
    })
  )
}

test('opens the row for a click on a plain cell', async () => {
  const onOpen = vi.fn()
  mountRow({ clickable: true, onOpen })

  const user = userOnFakeClock()

  await user.click(screen.getByText('plain text'))
  expect(onOpen).not.toHaveBeenCalled()
  await pastDoubleClick()

  expect(onOpen).toHaveBeenCalledOnce()
})

test('opens the row at once for a click without a pointer', async () => {
  const onOpen = vi.fn()
  mountRow({ clickable: true, onOpen })

  await fireEvent.click(screen.getByText('plain text'), { detail: 0 })

  expect(onOpen).toHaveBeenCalledOnce()
})

test('opens nothing when the row is not clickable', async () => {
  const onOpen = vi.fn()
  mountRow({ onOpen })
  const user = userOnFakeClock()

  await user.click(screen.getByText('plain text'))
  await pastDoubleClick()

  expect(onOpen).not.toHaveBeenCalled()
})

test('leaves a click in an interactive cell to that cell', async () => {
  const onOpen = vi.fn()
  mountRow({ clickable: true, onOpen })
  const user = userOnFakeClock()

  await user.click(screen.getByText('chip area'))
  await pastDoubleClick()

  expect(onOpen).not.toHaveBeenCalled()
})

test('leaves a click in a button cell to that cell', async () => {
  const onOpen = vi.fn()
  mountRow({ clickable: true, onOpen })
  const user = userOnFakeClock()

  await user.click(screen.getByText('button cell'))
  await pastDoubleClick()

  expect(onOpen).not.toHaveBeenCalled()
})

test('leaves a click on a link to the link', async () => {
  const onOpen = vi.fn()
  mountRow({ clickable: true, onOpen })
  const user = userOnFakeClock()

  await user.click(screen.getByText('a link'))
  await pastDoubleClick()

  expect(onOpen).not.toHaveBeenCalled()
})

test('opens nothing when the click ends marking text to copy', async () => {
  const onOpen = vi.fn()
  mountRow({ clickable: true, onOpen })
  const user = userOnFakeClock()

  await markText(user, screen.getByText('plain text'))
  await pastDoubleClick()

  expect(onOpen).not.toHaveBeenCalled()
})

test('opens nothing for a double-click marking text', async () => {
  const onOpen = vi.fn()
  mountRow({ clickable: true, onOpen })
  const user = userOnFakeClock()

  await user.dblClick(screen.getByText('plain text'))
  await pastDoubleClick()

  expect(onOpen).not.toHaveBeenCalled()
})

test('opens nothing when a press elsewhere follows the click', async () => {
  const onOpen = vi.fn()
  mountRow({ clickable: true, onOpen })
  const user = userOnFakeClock()

  await user.click(screen.getByText('plain text'))
  await user.pointer({ keys: '[MouseLeft]', target: document.body })
  await pastDoubleClick()

  expect(onOpen).not.toHaveBeenCalled()
})

test('only closes an open column filter on a click in the row', async () => {
  const onOpen = vi.fn()
  mountRow({ clickable: true, onOpen }, 'filter')
  const user = userOnFakeClock()

  await user.click(screen.getByRole('button', { name: 'Open filter' }))
  await user.click(screen.getByText('plain text'))
  await pastDoubleClick()

  expect(screen.queryByRole('group', { name: 'Filter Name' })).not.toBeInTheDocument()
  expect(onOpen).not.toHaveBeenCalled()
})

test.each([
  ['column filter', 'filter', 'Open filter'],
  ['flyout, which closes on the press already,', 'flyout', 'Open flyout']
] as const)(
  'only closes an open %s on a click on the open-details icon',
  async (_, popup, opener) => {
    const onOpenDetails = vi.fn()
    mountRow({ clickable: true }, popup, onOpenDetails)
    const user = userOnFakeClock()

    await user.click(screen.getByRole('button', { name: opener }))
    await user.click(screen.getByRole('button', { name: 'Open details' }))
    await pastDoubleClick()

    expect(onOpenDetails).not.toHaveBeenCalled()
  }
)

test('only closes an open flyout, which closes on the press already, on a click in the row', async () => {
  const onOpen = vi.fn()
  mountRow({ clickable: true, onOpen }, 'flyout')
  const user = userOnFakeClock()

  await user.click(screen.getByRole('button', { name: 'Open flyout' }))
  expect(screen.getByRole('dialog', { name: 'Range' })).toBeInTheDocument()
  await user.click(screen.getByText('plain text'))
  await pastDoubleClick()

  expect(screen.queryByRole('dialog', { name: 'Range' })).not.toBeInTheDocument()
  expect(onOpen).not.toHaveBeenCalled()
})

test('leaves a click with a modifier key to the browser', async () => {
  const onOpen = vi.fn()
  mountRow({ clickable: true, onOpen })

  const user = userOnFakeClock()
  await user.keyboard('{Meta>}')
  await user.click(screen.getByText('plain text'))
  await user.keyboard('{/Meta}')
  await pastDoubleClick()

  expect(onOpen).not.toHaveBeenCalled()
})
