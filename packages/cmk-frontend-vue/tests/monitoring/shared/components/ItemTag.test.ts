/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import ItemTag from '@/monitoring/shared/components/ItemTag.vue'
import type { ItemAction } from '@/monitoring/shared/components/cell/labelCellItem'

const ITEM = { text: 'linux' as TranslatedString }

const SELECT: ItemAction = { title: () => 'Pick linux' as TranslatedString }

test('emits the entry clicked on when its action selects', async () => {
  const { emitted } = render(ItemTag, { props: { item: ITEM, action: SELECT } })

  const button = screen.getByRole('button', { name: 'linux' })
  await userEvent.click(button)

  expect(button).toHaveAttribute('title', 'Pick linux')
  expect(emitted('select')).toStrictEqual([[ITEM]])
})

test('links to the page its action names instead of emitting the entry', async () => {
  const { emitted } = render(ItemTag, {
    props: { item: ITEM, action: { ...SELECT, href: () => 'hosts.py?tag=linux' } }
  })

  const link = screen.getByRole('link', { name: 'linux' })
  await userEvent.click(link)

  expect(link).toHaveAttribute('href', 'hosts.py?tag=linux')
  expect(link).toHaveAttribute('target', '_top')
  expect(emitted('select')).toBeUndefined()
})

test('stays plain without an action', () => {
  render(ItemTag, { props: { item: ITEM } })

  expect(screen.queryByRole('button', { name: 'linux' })).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'linux' })).not.toBeInTheDocument()
  expect(screen.getByTitle('linux')).toBeInTheDocument()
})
