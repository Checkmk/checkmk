/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import CmkAsyncContent from 'cmk-ui-library/components/CmkAsyncContent/CmkAsyncContent.vue'
import { defineComponent, h, markRaw } from 'vue'

const body = markRaw(
  defineComponent({
    props: { data: { type: String, default: '' }, label: { type: String, default: '' } },
    setup: (props) => () => h('div', { 'data-testid': 'body' }, `${props.label}${props.data}`)
  })
)

test('loads on mount and renders what came back', async () => {
  const load = vi.fn().mockResolvedValue('resolved content')

  render(CmkAsyncContent, { props: { component: body, load } })

  await screen.findByText('resolved content')
  expect(load).toHaveBeenCalledTimes(1)
})

test('forwards the static props alongside the loaded data', async () => {
  const load = vi.fn().mockResolvedValue('content')

  render(CmkAsyncContent, { props: { component: body, load, props: { label: 'Overview: ' } } })

  await screen.findByText('Overview: content')
})

test('renders content with nothing to load without waiting for anything', () => {
  render(CmkAsyncContent, { props: { component: body, props: { label: 'nothing to load' } } })

  expect(screen.getByText('nothing to load')).toBeInTheDocument()
})

test('shows an error with a retry that loads again', async () => {
  const load = vi
    .fn()
    .mockRejectedValueOnce(new Error('boom'))
    .mockResolvedValueOnce('recovered content')

  render(CmkAsyncContent, { props: { component: body, load } })

  await screen.findByText('Could not load this content.')
  await userEvent.click(screen.getByRole('button', { name: 'Retry' }))

  await screen.findByText('recovered content')
  expect(load).toHaveBeenCalledTimes(2)
})

test('shows the skeleton it was given in place of the generic indicator', async () => {
  const skeleton = markRaw(
    defineComponent({ setup: () => () => h('div', { 'data-testid': 'skeleton' }) })
  )
  let resolve: (value: string) => void = () => {}
  const load = vi.fn().mockReturnValue(
    new Promise<string>((r) => {
      resolve = r
    })
  )

  render(CmkAsyncContent, { props: { component: body, load, skeleton } })

  expect(screen.getByTestId('skeleton')).toBeInTheDocument()
  resolve('loaded')
  await screen.findByText('loaded')
})
