/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'

import GraphNotice, { type GraphNoticeVariant } from '@/graphing/components/GraphNotice.vue'

const notice = (): HTMLElement | null => document.querySelector('.graphing-graph-notice')

test('states the message for every variant', () => {
  for (const variant of ['error', 'loading', 'info'] satisfies GraphNoticeVariant[]) {
    const { unmount } = render(GraphNotice, {
      props: { variant, message: `${variant} happened` }
    })

    expect(screen.getByText(`${variant} happened`), variant).toBeInTheDocument()
    unmount()
  }
})

test('announces an error assertively and the other variants politely', () => {
  const { unmount } = render(GraphNotice, {
    props: { variant: 'error', message: 'Broken' }
  })
  expect(notice()).toHaveAttribute('role', 'alert')
  unmount()

  render(GraphNotice, { props: { variant: 'loading', message: 'Loading data …' } })
  expect(notice()).toHaveAttribute('role', 'status')
})

test('offers no retry unless asked for one', () => {
  render(GraphNotice, { props: { variant: 'error', message: 'Broken' } })

  expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
})

test('emits retry when the action is activated', async () => {
  const { emitted } = render(GraphNotice, {
    props: { variant: 'error', message: 'Broken', retry: true }
  })

  await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

  expect(emitted('retry')).toHaveLength(1)
})

test('renders the description as a second line when given', () => {
  render(GraphNotice, {
    props: {
      variant: 'info',
      message: 'No metrics added',
      description: 'Add a source to visualize your data'
    }
  })

  expect(screen.getByText('No metrics added')).toBeInTheDocument()
  expect(screen.getByText('Add a source to visualize your data')).toBeInTheDocument()
})
