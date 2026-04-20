/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import type { Mock } from 'vitest'
import { defineComponent, ref } from 'vue'

import FinalizeConfiguration, {
  type FinalizeState
} from '@/mode-otel/otel-configuration-steps/FinalizeConfiguration.vue'
import type { PostSaveAction } from '@/mode-otel/otel-configuration-steps/post_save_actions.ts'

function makeAction(
  key: string,
  result: 'ok' | { title: string; detail: string },
  { delayMs = 0 }: { delayMs?: number } = {}
): PostSaveAction {
  return {
    key,
    label: () => `Action ${key}`,
    execute: vi.fn(async () => {
      if (delayMs) {
        await new Promise((r) => setTimeout(r, delayMs))
      }
      return result === 'ok' ? { ok: true as const } : { ok: false as const, error: result }
    })
  }
}

function renderWithActions(
  actions: readonly PostSaveAction[],
  siteId: string | null = 'local',
  {
    collectorActivationAllowed,
    metricBackendAllowed,
    configName = 'my-config'
  }: {
    collectorActivationAllowed?: boolean
    configName?: string
    metricBackendAllowed?: boolean
  } = {}
) {
  const lastState = ref<FinalizeState>('idle')
  const compRef = ref<InstanceType<typeof FinalizeConfiguration>>()

  render(
    defineComponent({
      components: { FinalizeConfiguration },
      setup: () => ({
        compRef,
        lastState,
        actions,
        siteId,
        collectorActivationAllowed,
        metricBackendAllowed,
        configName
      }),
      template: `<FinalizeConfiguration ref="compRef" :site-id="siteId" :config-name="configName" :actions="actions" :collector-activation-allowed="collectorActivationAllowed" :metric-backend-allowed="metricBackendAllowed" @update:state="lastState = $event" />`
    })
  )

  return { compRef, lastState }
}

describe('FinalizeConfiguration', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  describe('initial render', () => {
    test('emits initial idle state', async () => {
      const { lastState } = renderWithActions([makeAction('a', 'ok')])
      await waitFor(() => expect(lastState.value).toBe('idle'))
    })

    test('lists every action label', async () => {
      renderWithActions([makeAction('a', 'ok'), makeAction('b', 'ok')])
      await screen.findByText('Action a')
      await screen.findByText('Action b')
    })
  })

  describe('successful run', () => {
    test('shows the running alert while actions execute, then success', async () => {
      const actionA = makeAction('a', 'ok', { delayMs: 10 })
      const { compRef, lastState } = renderWithActions([actionA])

      const runPromise = compRef.value!.runActions()

      // Running alert appears while the action is in flight.
      await waitFor(() => expect(lastState.value).toBe('running'))
      await screen.findByText('Verifying the OpenTelemetry configuration...')

      const ok = await runPromise

      expect(ok).toBe(true)
      expect(lastState.value).toBe('success')
      await screen.findByText('OpenTelemetry configuration saved successfully.')
      expect(actionA.execute).toHaveBeenCalledTimes(1)
    })

    test('runs actions in order and passes the site id', async () => {
      const actionA = makeAction('a', 'ok')
      const actionB = makeAction('b', 'ok')
      const { compRef } = renderWithActions([actionA, actionB], 'site42')

      const ok = await compRef.value!.runActions()

      expect(ok).toBe(true)
      expect(actionA.execute).toHaveBeenCalledWith({ siteId: 'site42', configName: 'my-config' })
      expect(actionB.execute).toHaveBeenCalledWith({ siteId: 'site42', configName: 'my-config' })
      // Order: A then B.
      const aOrder = (actionA.execute as Mock).mock.invocationCallOrder[0]!
      const bOrder = (actionB.execute as Mock).mock.invocationCallOrder[0]!
      expect(aOrder).toBeLessThan(bOrder)
    })
  })

  describe('error handling', () => {
    test('halts on first error and does not run subsequent actions', async () => {
      const actionA = makeAction('a', { title: 'Boom', detail: 'Something broke' })
      const actionB = makeAction('b', 'ok')
      const { compRef, lastState } = renderWithActions([actionA, actionB])

      const ok = await compRef.value!.runActions()

      expect(ok).toBe(false)
      expect(lastState.value).toBe('error')
      expect(actionA.execute).toHaveBeenCalledTimes(1)
      expect(actionB.execute).not.toHaveBeenCalled()
      await screen.findByText('Boom')
      await screen.findByText('Something broke')
    })

    test('retrying after an error restarts from a clean state', async () => {
      let shouldFail = true
      const flaky: PostSaveAction = {
        key: 'flaky',
        label: () => 'Flaky action',
        execute: vi.fn(async () =>
          shouldFail
            ? { ok: false as const, error: { title: 'Transient', detail: 'Retry me' } }
            : { ok: true as const }
        )
      }
      const { compRef, lastState } = renderWithActions([flaky])

      // First run fails.
      const firstOk = await compRef.value!.runActions()
      expect(firstOk).toBe(false)
      expect(lastState.value).toBe('error')

      // Second run succeeds. Error alert should be replaced by success.
      shouldFail = false
      const secondOk = await compRef.value!.runActions()

      expect(secondOk).toBe(true)
      expect(lastState.value).toBe('success')
      expect(flaky.execute).toHaveBeenCalledTimes(2)
      await screen.findByText('OpenTelemetry configuration saved successfully.')
    })

    test('refuses to run without a selected site', async () => {
      const actionA = makeAction('a', 'ok')
      const { compRef, lastState } = renderWithActions([actionA], null)

      const ok = await compRef.value!.runActions()

      expect(ok).toBe(false)
      expect(lastState.value).toBe('error')
      expect(actionA.execute).not.toHaveBeenCalled()
    })
  })

  describe('edition filtering', () => {
    test('filters out enableCollector action when collectorActivationAllowed is false', async () => {
      const collector: PostSaveAction = {
        key: 'enableCollector',
        label: () => 'OpenTelemetry Collector activation',
        execute: vi.fn(async () => ({ ok: true as const }))
      }
      const other = makeAction('other', 'ok')
      renderWithActions([collector, other], 'local', {
        collectorActivationAllowed: false
      })

      await screen.findByText('Action other')
      expect(screen.queryByText('OpenTelemetry Collector activation')).toBeNull()
    })

    test('keeps enableCollector action when collectorActivationAllowed is true', async () => {
      const collector: PostSaveAction = {
        key: 'enableCollector',
        label: () => 'OpenTelemetry Collector activation',
        execute: vi.fn(async () => ({ ok: true as const }))
      }
      const other = makeAction('other', 'ok')
      renderWithActions([collector, other], 'local', {
        collectorActivationAllowed: true
      })

      await screen.findByText('OpenTelemetry Collector activation')
      await screen.findByText('Action other')
    })

    test('keeps enableCollector action when collectorActivationAllowed is not passed', async () => {
      // Regression: Vue 3 coerces an unpassed Boolean prop to `false`. Without
      // withDefaults, that silently strips enableCollector and the save flow
      // completes without hitting the REST API.
      const collector: PostSaveAction = {
        key: 'enableCollector',
        label: () => 'OpenTelemetry Collector activation',
        execute: vi.fn(async () => ({ ok: true as const }))
      }
      const other = makeAction('other', 'ok')
      const { compRef } = renderWithActions([collector, other], 'local')

      await screen.findByText('OpenTelemetry Collector activation')
      await screen.findByText('Action other')

      const ok = await compRef.value!.runActions()
      expect(ok).toBe(true)
      expect(collector.execute).toHaveBeenCalledTimes(1)
    })

    test('filters out enableMetricBackend action when metricBackendAllowed is false', async () => {
      const metricBackend: PostSaveAction = {
        key: 'enableMetricBackend',
        label: () => 'Metric backend connection',
        execute: vi.fn(async () => ({ ok: true as const }))
      }
      const other = makeAction('other', 'ok')
      renderWithActions([metricBackend, other], 'local', {
        metricBackendAllowed: false
      })

      await screen.findByText('Action other')
      expect(screen.queryByText('Metric backend connection')).toBeNull()
    })

    test('keeps enableMetricBackend action when metricBackendAllowed is true', async () => {
      const metricBackend: PostSaveAction = {
        key: 'enableMetricBackend',
        label: () => 'Metric backend connection',
        execute: vi.fn(async () => ({ ok: true as const }))
      }
      const other = makeAction('other', 'ok')
      renderWithActions([metricBackend, other], 'local', {
        metricBackendAllowed: true
      })

      await screen.findByText('Metric backend connection')
      await screen.findByText('Action other')
    })

    test('keeps enableMetricBackend action when metricBackendAllowed is not passed', async () => {
      // Regression: Vue 3 coerces an unpassed Boolean prop to `false`. Without
      // withDefaults, that silently strips enableMetricBackend and the save
      // flow completes without hitting the REST API. This path is what the
      // Prometheus QuickSetup relies on — it never passes the prop.
      const metricBackend: PostSaveAction = {
        key: 'enableMetricBackend',
        label: () => 'Metric backend connection',
        execute: vi.fn(async () => ({ ok: true as const }))
      }
      const other = makeAction('other', 'ok')
      const { compRef } = renderWithActions([metricBackend, other], 'local')

      await screen.findByText('Metric backend connection')
      await screen.findByText('Action other')

      const ok = await compRef.value!.runActions()
      expect(ok).toBe(true)
      expect(metricBackend.execute).toHaveBeenCalledTimes(1)
    })
  })
})
