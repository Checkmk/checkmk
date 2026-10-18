<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import ConnectionTestStateIcon from './ConnectionTestStateIcon.vue'

type Phase = components['schemas']['_ConnectionTestPhase']
type Step = components['schemas']['_ConnectionTestStep']
type Status = components['schemas']['_ConnectionTestStatus']
type Settings = Pick<
  components['schemas']['_CentralConnectionTest'],
  'centrally_routed_features' | 'address_seen_by_central'
>

type State =
  | { type: 'idle' }
  | { type: 'starting' }
  | { type: 'running'; phases: Phase[]; aborting: boolean }
  | { type: 'failed'; message: string }
  | ({ type: 'done' } & Status)

const POLL_INTERVAL_MS = 1000

const props = defineProps<{
  siteId: string
  settings: Settings
}>()

const { _t } = usei18n()

const state = ref<State>({ type: 'idle' })
const testedSettings = ref<Partial<Settings> | null>(null)
const busy = computed(() => state.value.type === 'starting' || state.value.type === 'running')
const restartWarning = computed(() =>
  state.value.type === 'done' ? state.value.restart_warning : undefined
)
const outdated = computed(
  () => testedSettings.value !== null && !sameSettings(testedSettings.value, props.settings)
)
let pollTimer: ReturnType<typeof setTimeout> | undefined
let unmounted = false

onMounted(() => void resume())

onBeforeUnmount(() => {
  unmounted = true
  clearTimeout(pollTimer)
})

watch(
  () => props.settings,
  () => {
    if (!busy.value) {
      reset()
    }
  }
)

async function resume(): Promise<void> {
  let status: Status
  try {
    status = unwrap(
      await client.GET('/domain-types/data_backend/actions/show_central_connection_test/invoke')
    )
  } catch {
    return
  }
  if (state.value.type !== 'idle' || !status.running || status.site_id !== props.siteId) {
    return
  }
  testedSettings.value = status
  show(status)
}

async function start(allowRestart: boolean): Promise<void> {
  state.value = { type: 'starting' }
  testedSettings.value = props.settings
  let status: Status
  try {
    status = unwrap(
      await client.POST('/domain-types/data_backend/actions/test_central_connection/invoke', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: { site_id: props.siteId, ...props.settings, allow_restart: allowRestart }
      })
    )
  } catch (error) {
    state.value = errorState(error)
    return
  }
  show(status)
  if (status.running) {
    clearTimeout(pollTimer)
    await poll()
  }
}

async function abort(): Promise<void> {
  if (state.value.type !== 'running') {
    return
  }
  state.value = { ...state.value, aborting: true }
  try {
    unwrap(
      await client.POST('/domain-types/data_backend/actions/abort_central_connection_test/invoke')
    )
  } catch (error) {
    clearTimeout(pollTimer)
    state.value = errorState(error)
  }
}

function reset(): void {
  state.value = { type: 'idle' }
  testedSettings.value = null
}

async function poll(): Promise<void> {
  try {
    show(
      unwrap(
        await client.GET('/domain-types/data_backend/actions/show_central_connection_test/invoke')
      )
    )
  } catch (error) {
    state.value = errorState(error)
  }
}

function show(status: Status): void {
  if (!status.running) {
    state.value = { type: 'done', ...status }
    return
  }
  const aborting = state.value.type === 'running' && state.value.aborting
  // Keep the planned steps until the test reports.
  const phases =
    status.phases.length === 0 && 'phases' in state.value ? state.value.phases : status.phases
  state.value = { type: 'running', phases, aborting }
  if (!unmounted) {
    pollTimer = setTimeout(() => void poll(), POLL_INTERVAL_MS)
  }
}

function sameSettings(some: Partial<Settings>, other: Partial<Settings>): boolean {
  const features = (settings: Partial<Settings>) =>
    [...(settings.centrally_routed_features ?? [])].sort().join()
  return (
    features(some) === features(other) &&
    (some.address_seen_by_central ?? '') === (other.address_seen_by_central ?? '')
  )
}

function errorState(error: unknown): State {
  if (!(error instanceof CmkApiError)) {
    return { type: 'failed', message: String(error) }
  }
  const body = (error.body ?? {}) as { detail?: string }
  return { type: 'failed', message: body.detail ?? error.message }
}

function shownState(stepState: Step['state']): Step['state'] | 'warning' {
  return restartWarning.value !== undefined && stepState === 'failed' ? 'warning' : stepState
}

function failedSteps(phases: Phase[]): Step[] {
  return phases.flatMap((phase) => phase.steps.filter((step) => step.state === 'failed'))
}

function failureText(step: Step): string {
  return [step.message, step.details].filter((text) => text !== '').join(' ')
}
</script>

<template>
  <div class="data-backend-central-connection-test">
    <div class="data-backend-central-connection-test__actions">
      <CmkButton :disabled="busy" @click="() => void start(false)">
        {{ _t('Test connection') }}
      </CmkButton>
      <CmkButton
        v-if="state.type === 'running'"
        variant="secondary"
        :disabled="state.aborting"
        @click="() => void abort()"
      >
        {{ _t('Abort test') }}
      </CmkButton>
    </div>
    <CmkAlert
      v-if="outdated"
      variant="info"
      size="small"
      :text="_t('The settings changed since the test started. Test again to check them.')"
    />
    <CmkAlert
      v-if="restartWarning !== undefined"
      variant="warning"
      :text="untranslated(restartWarning)"
      :main-button="{ title: _t('Test anyway'), onclick: () => void start(true) }"
      :optional-button="{ title: _t('Cancel'), onclick: reset }"
    />
    <ul v-if="'phases' in state" class="data-backend-central-connection-test__phases">
      <li v-for="(phase, phaseIndex) in state.phases" :key="phaseIndex">
        <span class="data-backend-central-connection-test__entry">
          <ConnectionTestStateIcon :state="shownState(phase.state)" />{{ phase.title }}
        </span>
        <ul class="data-backend-central-connection-test__steps">
          <li v-for="(step, stepIndex) in phase.steps" :key="stepIndex">
            <span class="data-backend-central-connection-test__entry">
              <ConnectionTestStateIcon :state="shownState(step.state)" />{{ step.title }}
            </span>
          </li>
        </ul>
      </li>
    </ul>
    <CmkAlert
      v-if="state.type === 'failed'"
      variant="error"
      :heading="_t('The connection could not be tested')"
      :text="untranslated(state.message)"
    />
    <template v-else-if="state.type === 'done' && restartWarning === undefined">
      <CmkAlert
        v-if="state.aborted !== undefined"
        variant="info"
        :heading="_t('The test was aborted')"
        :text="untranslated(state.aborted)"
      />
      <CmkAlert
        v-if="state.problem !== undefined"
        variant="error"
        :heading="_t('The connection could not be tested')"
        :text="untranslated(state.problem)"
      />
      <CmkAlert
        v-for="(step, index) in failedSteps(state.phases)"
        :key="index"
        variant="error"
        :text="untranslated(failureText(step))"
      />
    </template>
  </div>
</template>

<style scoped>
.data-backend-central-connection-test {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--spacing);
  margin-top: var(--spacing);
}

.data-backend-central-connection-test__actions {
  display: flex;
  gap: var(--dimension-4);
}

.data-backend-central-connection-test__phases,
.data-backend-central-connection-test__steps {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.data-backend-central-connection-test__steps {
  margin-top: var(--dimension-3);
  padding-left: var(--dimension-8);
}

.data-backend-central-connection-test__entry {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}
</style>
