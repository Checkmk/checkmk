/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import CmkCode from 'cmk-ui-library/components/CmkCode.vue'

const codeText = `${'first: line\n'.repeat(10)}last: line`

test('long code can be expanded and collapsed by default', async () => {
  const user = userEvent.setup()
  render(CmkCode, { props: { codeText } })
  expect(screen.queryByText(/last: line/)).not.toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Show more' }))

  expect(screen.getByText(/last: line/)).toBeVisible()

  await user.click(screen.getByRole('button', { name: 'Show less' }))

  expect(screen.queryByText(/last: line/)).not.toBeInTheDocument()
})

test('non-collapsible code displays the entire content without a toggle', () => {
  render(CmkCode, { props: { codeText, collapsible: false, wrap: true } })

  expect(screen.getByText(/last: line/)).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Show more' })).not.toBeInTheDocument()
})

test('code updates when its content and collapsible setting change', async () => {
  const { rerender } = render(CmkCode, { props: { codeText: 'initial content' } })

  await rerender({ codeText, collapsible: false })

  expect(screen.queryByText('initial content')).not.toBeInTheDocument()
  expect(screen.getByText(/last: line/)).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Show more' })).not.toBeInTheDocument()

  await rerender({ codeText, collapsible: true })

  expect(screen.queryByText(/last: line/)).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Show more' })).toBeVisible()
})
