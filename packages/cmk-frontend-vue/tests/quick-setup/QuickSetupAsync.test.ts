/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'

import QuickSetupAsync from '@/quick-setup/QuickSetupAsync.vue'
import type { Action, QuickSetupGuidedResponse } from '@/quick-setup/rest-api/response_schemas'

import { wrapInSuspense } from '../dashboard/utils'

const api = `${location.origin}/api/1.0/objects`
const setupUrl = `${api}/quick_setup/kubernetes`
const server = setupServer()
const back = { id: 'back', label: 'Back', aria_label: 'Back' }
const action = (id: string, label: string): Action => ({
  id,
  button: { id, label, aria_label: label },
  load_wait_label: 'Preparing'
})

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => {
  // Vue logs this once when mounting an async component in Suspense.
  vi.spyOn(console, 'info').mockImplementation((message: unknown) => {
    expect(message).toBe('<Suspense> is an experimental feature and its API will likely change.')
  })
})
afterEach(() => {
  cleanup()
  server.resetHandlers()
  vi.restoreAllMocks()
})
afterAll(() => server.close())

async function startDeployment() {
  let pullSelected = false
  const overview: QuickSetupGuidedResponse = {
    quick_setup_id: 'kubernetes',
    guided_mode_string: 'Guided',
    overview_mode_string: 'Overview',
    overviews: [
      { title: 'Configure cluster', sub_title: null, is_applicable: true },
      { title: 'Deploy agent', sub_title: null, is_applicable: true },
      { title: 'Pull mode base URL', sub_title: null, is_applicable: false }
    ],
    stage: { components: [], actions: [action('configure', 'Next')] },
    actions: [action('save', 'Save configuration')],
    prev_button: back
  }
  const result = () => ({
    stage_recap: [
      {
        widget_type: 'code',
        title: 'values.yaml',
        code: 'clusterName: example\n',
        download_filename: 'values.yaml'
      }
    ],
    stage_applicability: [true, true, pullSelected],
    validation_errors: null,
    background_job_exception: null
  })
  server.use(
    http.get(setupUrl, () => HttpResponse.json(overview)),
    http.get(`${setupUrl}/quick_setup_stage/1`, () =>
      HttpResponse.json({
        components: [],
        actions: [
          action('deploy_push', 'Deploy with push'),
          action('deploy_pull', 'Deploy with pull')
        ],
        prev_button: back
      })
    ),
    http.get(`${setupUrl}/quick_setup_stage/2`, () =>
      HttpResponse.json({
        components: [],
        actions: [action('confirm_url', 'Confirm URL')],
        prev_button: back
      })
    ),
    http.post(`${setupUrl}/actions/run-stage-action/invoke`, async ({ request }) => {
      const { stage_action_id: id } = (await request.json()) as { stage_action_id: string }
      if (id.startsWith('deploy_')) {
        pullSelected = id === 'deploy_pull'
        return HttpResponse.json({
          domainType: 'background_job',
          id: 'deployment',
          extensions: { site_id: 'site' }
        })
      }
      return HttpResponse.json({ ...result(), stage_recap: [] })
    }),
    http.get(`${api}/background_job/deployment`, () =>
      HttpResponse.json({
        extensions: { active: false, status: { log_info: { JobProgressUpdate: [] } } }
      })
    ),
    http.get(`${api}/quick_setup_stage_action_result/deployment`, () => HttpResponse.json(result()))
  )
  render(
    wrapInSuspense(QuickSetupAsync, {
      props: {
        quick_setup_id: 'kubernetes',
        mode: 'guided',
        toggle_enabled: false,
        object_id: null
      }
    })
  )
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Next' }))
  await screen.findByRole('button', { name: 'Deploy with push' })
  return user
}

test('push skips the URL stage in both forward and backward navigation', async () => {
  const user = await startDeployment()
  expect(screen.queryByText('Pull mode base URL')).not.toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Deploy with push' }))

  await screen.findByRole('button', { name: 'Save configuration' })
  expect(screen.queryByText('Pull mode base URL')).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Download' })).toHaveAttribute('download', 'values.yaml')

  await user.click(screen.getByRole('button', { name: 'Back' }))

  await screen.findByRole('button', { name: 'Deploy with push' })
  expect(screen.queryByRole('button', { name: 'Confirm URL' })).not.toBeInTheDocument()
})

test('pull shows deployment downloads before allowing URL confirmation and saving', async () => {
  const user = await startDeployment()

  await user.click(screen.getByRole('button', { name: 'Deploy with pull' }))

  const confirm = await screen.findByRole('button', { name: 'Confirm URL' })
  expect(screen.getByRole('link', { name: 'Download' })).toHaveAttribute('download', 'values.yaml')
  expect(screen.queryByRole('button', { name: 'Save configuration' })).not.toBeInTheDocument()

  await user.click(confirm)

  await screen.findByRole('button', { name: 'Save configuration' })
})

test('changing connection mode hides and re-enables the final URL stage', async () => {
  const user = await startDeployment()
  await user.click(screen.getByRole('button', { name: 'Deploy with pull' }))
  await screen.findByRole('button', { name: 'Confirm URL' })

  await user.click(screen.getByRole('button', { name: 'Back' }))
  await user.click(await screen.findByRole('button', { name: 'Deploy with push' }))

  await screen.findByRole('button', { name: 'Save configuration' })
  expect(screen.queryByText('Pull mode base URL')).not.toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Back' }))
  await user.click(await screen.findByRole('button', { name: 'Deploy with pull' }))

  await screen.findByRole('button', { name: 'Confirm URL' })
  expect(screen.queryByRole('button', { name: 'Save configuration' })).not.toBeInTheDocument()
})
