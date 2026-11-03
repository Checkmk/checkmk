/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, within } from '@testing-library/vue'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'

import CentralConnectionTest from '@/data-backend/CentralConnectionTest.vue'

type ConnectionTest = components['schemas']['_CentralConnectionTest']
type Status = components['schemas']['_ConnectionTestStatus']
type Phase = components['schemas']['_ConnectionTestPhase']
type Step = components['schemas']['_ConnectionTestStep']
type State = Step['state']

const START = '/domain-types/data_backend/actions/test_central_connection/invoke'
const SHOW = '/domain-types/data_backend/actions/show_central_connection_test/invoke'
const ABORT = '/domain-types/data_backend/actions/abort_central_connection_test/invoke'
const RESTART_WARNING = 'Testing the connection restarts it twice.'
const RESTART_CHECK = 'Check whether the data backend must be started or restarted'

function step(title: string, state: State, message: string = '', details: string = ''): Step {
  return { title, state, message, details }
}

function phase(title: string, state: State, steps: Step[]): Phase {
  return { title, state, steps }
}

const server = useMswServer(
  restApiHttp.post(START, ({ response }) => response(200).json({ running: true, phases: [] })),
  restApiHttp.get(SHOW, ({ response }) => response(200).json({ running: false, phases: [] }))
)

function showing(status: Status): void {
  server.use(restApiHttp.get(SHOW, ({ response }) => response(200).json(status)))
}

function renderTest(): ReturnType<typeof render> {
  return render(CentralConnectionTest, {
    props: { siteId: 'remote1', settings: { centrally_routed_features: ['telemetry'] } }
  })
}

async function startTest(): Promise<void> {
  await userEvent.click(screen.getByRole('button', { name: 'Test connection' }))
}

function stepIcon(title: string, stateLabel: string): HTMLElement | null {
  return within(screen.getByText(title)).queryByRole('img', { name: stateLabel })
}

function planToStart(restartCheck: State, start: State): Phase[] {
  const restartRefused = restartCheck === 'failed'
  return [
    phase('Set up this site temporarily', restartRefused ? 'failed' : start, [
      step(RESTART_CHECK, restartCheck, restartRefused ? RESTART_WARNING : ''),
      step('Start the data backend', start)
    ])
  ]
}

function restartingCentral(restartConsented: ConnectionTest['allow_restart'][]): void {
  server.use(
    restApiHttp.post(START, async ({ request, response }) => {
      const body = await request.json()
      restartConsented.push(body.allow_restart)
      return response(200).json(
        body.allow_restart
          ? { running: true, phases: planToStart('passed', 'pending') }
          : {
              running: false,
              phases: planToStart('failed', 'pending'),
              restart_warning: RESTART_WARNING
            }
      )
    })
  )
  showing({ running: false, phases: planToStart('passed', 'passed') })
}

function runningTest(tested: Pick<Status, 'site_id' | 'address_seen_by_central'>): void {
  showing({
    running: true,
    centrally_routed_features: ['telemetry'],
    ...tested,
    phases: [
      phase('Verify the connection between the sites', 'running', [
        step('Connect via HTTPS', 'running')
      ])
    ]
  })
}

test('the data backend is restarted only after consent to the warning above the steps', async () => {
  const restartConsented: ConnectionTest['allow_restart'][] = []
  restartingCentral(restartConsented)
  renderTest()

  await startTest()
  const warning = await screen.findByText(RESTART_WARNING)
  expect(stepIcon(RESTART_CHECK, 'Warning')).toBeVisible()
  expect(stepIcon('Start the data backend', 'Pending')).toBeVisible()
  expect(
    warning.compareDocumentPosition(screen.getByText('Start the data backend')) &
      Node.DOCUMENT_POSITION_FOLLOWING
  ).toBeTruthy()
  await userEvent.click(screen.getByRole('button', { name: 'Test anyway' }))

  expect(
    await within(screen.getByText('Start the data backend')).findByRole('img', { name: 'Passed' })
  ).toBeVisible()
  expect(restartConsented).toEqual([false, true])
})

test('declining the restart leaves everything as it was', async () => {
  const restartConsented: ConnectionTest['allow_restart'][] = []
  restartingCentral(restartConsented)
  renderTest()

  await startTest()
  await userEvent.click(await screen.findByRole('button', { name: 'Cancel' }))

  expect([screen.queryByText('Start the data backend'), restartConsented]).toEqual([null, [false]])
})

test('the planned steps show up as soon as the test starts', async () => {
  server.use(
    restApiHttp.post(START, ({ response }) =>
      response(200).json({ running: true, phases: planToStart('passed', 'pending') })
    )
  )
  showing({ running: true, phases: [] })
  renderTest()

  await startTest()

  expect(await screen.findByText('Start the data backend')).toBeVisible()
})

test('a running test shows the state of every step', async () => {
  showing({
    running: true,
    phases: [
      phase('Set up this site temporarily', 'failed', [
        step('Start the data backend', 'passed'),
        step('Create the test database', 'failed')
      ]),
      phase('Undo the temporary setup', 'running', [
        step('Delete the test databases', 'running'),
        step('Stop the data backend', 'pending')
      ])
    ]
  })
  renderTest()

  await startTest()
  await screen.findByText('Undo the temporary setup')

  expect([
    stepIcon('Set up this site temporarily', 'Failed'),
    stepIcon('Start the data backend', 'Passed'),
    stepIcon('Create the test database', 'Failed'),
    stepIcon('Undo the temporary setup', 'Running'),
    stepIcon('Delete the test databases', 'Running'),
    stepIcon('Stop the data backend', 'Pending')
  ]).not.toContain(null)
})

test('a running test can be aborted', async () => {
  let aborts = 0
  runningTest({ site_id: 'other_remote' })
  server.use(
    restApiHttp.post(ABORT, ({ response }) => {
      aborts += 1
      return response(204).empty()
    })
  )
  renderTest()

  await startTest()
  await userEvent.click(await screen.findByRole('button', { name: 'Abort test' }))

  expect([
    aborts,
    screen.getByRole<HTMLButtonElement>('button', { name: 'Abort test' }).disabled
  ]).toEqual([1, true])
})

test.each([
  {
    outcome: 'refused',
    respond: () =>
      server.use(
        restApiHttp.post(START, ({ response }) =>
          response(409).json({
            title: 'Conflict',
            detail: 'The remote site stores no data centrally.',
            status: 409
          })
        )
      ),
    reason: 'The remote site stores no data centrally.'
  },
  {
    outcome: 'could not run',
    respond: () => showing({ running: false, phases: [], problem: 'The data backend is busy.' }),
    reason: 'The data backend is busy.'
  },
  {
    outcome: 'was aborted',
    respond: () => showing({ running: false, phases: [], aborted: 'You aborted the test.' }),
    reason: 'You aborted the test.'
  },
  {
    outcome: 'failed a step',
    respond: () =>
      showing({
        running: false,
        phases: [
          phase('Verify the database access', 'failed', [
            step('Read the test database', 'failed', 'Check the address.', 'Code: 516')
          ])
        ]
      }),
    reason: 'Check the address. Code: 516'
  }
])('a test that $outcome tells why', async ({ respond, reason }) => {
  respond()
  renderTest()

  await startTest()

  expect(await screen.findByText(reason)).toBeVisible()
})

test('a running test of unsaved settings shows up again', async () => {
  runningTest({ site_id: 'remote1', address_seen_by_central: '10.0.0.3' })

  renderTest()

  expect(await screen.findByText('Connect via HTTPS')).toBeVisible()
  expect(
    screen.getByText('The settings changed since the test started. Test again to check them.')
  ).toBeVisible()
})

test('changing the settings during a test tells that it checks the old ones', async () => {
  runningTest({ site_id: 'other_remote' })
  const { rerender } = renderTest()
  await startTest()
  await screen.findByText('Connect via HTTPS')

  await rerender({
    settings: { centrally_routed_features: ['telemetry'], address_seen_by_central: '10.0.0.3' }
  })

  expect(
    screen.getByText('The settings changed since the test started. Test again to check them.')
  ).toBeVisible()
})

test('changing the settings clears the result', async () => {
  showing({ running: false, phases: planToStart('passed', 'passed') })
  const { rerender } = renderTest()
  await startTest()
  await screen.findByText('Start the data backend')

  await rerender({
    settings: { centrally_routed_features: ['telemetry'], address_seen_by_central: '10.0.0.3' }
  })

  expect(screen.queryByText('Start the data backend')).toBeNull()
})
