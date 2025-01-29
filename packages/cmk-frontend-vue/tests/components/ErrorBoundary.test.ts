/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { fireEvent, render, screen } from '@testing-library/vue'
import DemoErrorBoundary from '@/components/_demo/DemoErrorBoundary.vue'

test('ErrorBoundary shows full stack', async () => {
  render(DemoErrorBoundary, {
    props: { screenshotMode: false }
  })

  const button = screen.getByRole<HTMLButtonElement>('button', { name: 'throw new CmkError()' })
  // we just tested that CmkErrorBoundary renders the content passed in the <slot>

  // now click the button
  const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
  await fireEvent.click(button)
  expect(spy.mock.calls.length).toBe(1)
  spy.mockRestore()

  // we now see a unspecific error message:
  screen.getByText('An unknown error occurred.', { exact: false })

  // and click the button for more details:
  const details = screen.getByRole<HTMLButtonElement>('button', { name: 'Show details' })
  await fireEvent.click(details)

  // and make sure we see the whole error trace now:
  screen.getByText('something happened in code we can not control', { exact: false })
  screen.getByText('DemoError: internal error handler, but keeps', { exact: false })
  screen.getByText('DemoErrorContext', { exact: false })
  screen.getByText('this is a cmk error', { exact: false })
})
