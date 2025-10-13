/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent } from 'vue'

import { CmkError } from '@/lib/error.ts'

import { useCmkErrorBoundary } from '@/components/CmkErrorBoundary'

test('CmkErrorBoundary shows full stack', async () => {
  class DemoError<T extends Error> extends CmkError<T> {
    override name = 'DemoError'
    override getContext(): string {
      return 'DemoErrorContext'
    }
  }

  const testComponent = defineComponent({
    components: {},
    setup() {
      // eslint-disable-next-line @typescript-eslint/naming-convention
      const { CmkErrorBoundary } = useCmkErrorBoundary()
      function throwCmkError() {
        try {
          try {
            throw new Error('something happened in code we can not control')
          } catch (error: unknown) {
            throw new DemoError('internal error handler, but keeps bubbeling', error as Error)
          }
        } catch (error: unknown) {
          throw new CmkError('this is a cmk error', error as Error)
        }
      }

      function throwError(message: string) {
        throw new Error(message)
      }
      return {
        CmkErrorBoundary,
        throwError,
        throwCmkError
      }
    },
    template: `
      <div>
        <component :is=CmkErrorBoundary>
          <button @click="throwError('this is a test error')">throw new Error()</button>
          <button @click="throwCmkError()">throw new CmkError()</button>
        </component>
      </div>
      <button @click="throwError('another error')">throw new Error() outside error boundary</button>
    `
  })

  render(testComponent)

  const button = screen.getByRole<HTMLButtonElement>('button', { name: 'throw new CmkError()' })
  // we just tested that CmkErrorBoundary renders the content passed in the <slot>

  // now click the button
  const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
  await fireEvent.click(button)
  expect(spy.mock.calls.length).toBe(1)
  spy.mockRestore()

  // we now see a unspecific error message:
  screen.getByText('An unexpected error occurred', { exact: false })

  // and click the button for more details:
  const details = screen.getByRole<HTMLButtonElement>('button', { name: 'Details' })
  await fireEvent.click(details)

  // and make sure we see the whole error trace now:
  await screen.findByText('something happened in code we can not control', { exact: false })
  screen.getByText('DemoError: internal error handler, but keeps', { exact: false })
  screen.getByText('DemoErrorContext', { exact: false })
  screen.getAllByText('this is a cmk error', { exact: false })
})
