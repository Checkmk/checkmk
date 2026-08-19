/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { useCmkErrorBoundary } from 'cmk-ui-library/components/CmkErrorBoundary'
import { CmkError } from 'cmk-ui-library/lib/error.ts'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { defineComponent } from 'vue'

const CRASH_REPORT_URL = '/domain-types/javascript_crash_report/collections/all'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST')
  postSpy.mockResolvedValue({
    data: {
      domainType: 'javascript_crash_report',
      id: 'a-crash-id',
      links: [],
      extensions: {
        crash_type: 'javascript',
        crash_report_url: 'crash.py?component=javascript&ident=a-crash-id'
      }
    },
    error: undefined,
    response: new Response(null, { status: 201 })
  } as never)
})

afterEach(() => {
  vi.restoreAllMocks()
})

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

test('CmkErrorBoundary stores the caught error as a crash report', async () => {
  const testComponent = defineComponent({
    name: 'DemoComponent',
    setup() {
      // eslint-disable-next-line @typescript-eslint/naming-convention
      const { CmkErrorBoundary } = useCmkErrorBoundary()
      function throwError() {
        throw new RangeError('a crash worth reporting')
      }
      return { CmkErrorBoundary, throwError }
    },
    template: `
      <component :is=CmkErrorBoundary>
        <button @click="throwError()">throw</button>
      </component>
    `
  })

  render(testComponent)

  const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  await fireEvent.click(screen.getByRole<HTMLButtonElement>('button', { name: 'throw' }))
  consoleSpy.mockRestore()

  expect(postSpy).toHaveBeenCalledTimes(1)
  const [url, options] = postSpy.mock.calls[0]
  expect(url).toBe(CRASH_REPORT_URL)
  expect(options.body.error_name).toBe('RangeError')
  expect(options.body.error_message).toBe('a crash worth reporting')
  expect(options.body.component).toBe('DemoComponent')
  expect(options.body.url).toBe(window.location.href)
})

test('CmkErrorBoundary links to the crash report it created', async () => {
  const testComponent = defineComponent({
    name: 'LinkingComponent',
    setup() {
      // eslint-disable-next-line @typescript-eslint/naming-convention
      const { CmkErrorBoundary } = useCmkErrorBoundary()
      function throwError() {
        throw new RangeError('a crash worth linking')
      }
      return { CmkErrorBoundary, throwError }
    },
    template: `
      <component :is=CmkErrorBoundary>
        <button @click="throwError()">throw</button>
      </component>
    `
  })

  render(testComponent)

  const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  await fireEvent.click(screen.getByRole<HTMLButtonElement>('button', { name: 'throw' }))
  consoleSpy.mockRestore()

  const link = await screen.findByRole<HTMLAnchorElement>('link', { name: 'Open crash report' })
  expect(link).toHaveAttribute('href', 'crash.py?component=javascript&ident=a-crash-id')
  screen.getByText('A crash report has been created', { exact: false })
})

test('CmkErrorBoundary says so when no crash report could be stored', async () => {
  postSpy.mockResolvedValue({
    data: undefined,
    error: {},
    response: new Response('', { status: 500, statusText: 'Internal Server Error' })
  } as never)

  const testComponent = defineComponent({
    name: 'FailingReportComponent',
    setup() {
      // eslint-disable-next-line @typescript-eslint/naming-convention
      const { CmkErrorBoundary } = useCmkErrorBoundary()
      function throwError() {
        throw new RangeError('a crash that cannot be stored')
      }
      return { CmkErrorBoundary, throwError }
    },
    template: `
      <component :is=CmkErrorBoundary>
        <button @click="throwError()">throw</button>
      </component>
    `
  })

  render(testComponent)

  const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  await fireEvent.click(screen.getByRole<HTMLButtonElement>('button', { name: 'throw' }))

  await screen.findByText('No crash report could be stored for this error.', { exact: false })
  consoleSpy.mockRestore()
})
