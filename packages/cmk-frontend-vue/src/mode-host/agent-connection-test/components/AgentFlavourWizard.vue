<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import CmkWizard from 'cmk-ui-library/components/CmkWizard'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref, watch } from 'vue'

import type { AgentSlideOutTabs } from '../lib/type_def'
import InstallAgentStep from './steps/InstallAgentStep.vue'
import RegisterAgent from './steps/RegisterAgent.vue'
import SaveHostStep from './steps/SaveHostStep.vue'
import TestConnectionStep from './steps/TestConnectionStep.vue'

const props = defineProps<{
  tab: AgentSlideOutTabs
  saveHost: boolean
  hostExists: boolean
  setupError: boolean
  agentInstalled: boolean
  isPushMode: boolean
  hostName: string
  siteId: string
  userSettingsUrl: string
  closeButtonTitle: TranslatedString
  agentReceiverPortIsDefault: boolean
  /** Package remembered across a save-host reload, for this flavour only. */
  restoredPackageId?: string | undefined
}>()

/** The shell preference is shared across flavours; progress is not. */
const shellId = defineModel<string>('shellId', { default: '' })

const emit = defineEmits<{ close: []; saveHost: [packageId: string] }>()

type StepKind = 'save-host' | 'install' | 'register' | 'test-connection'

/**
 * The steps this flavour actually shows. `CmkWizard` compares `currentStep`
 * against each step's `index` and its `next()` is a plain increment, so the
 * indices have to be dense — deriving them from this list is what keeps a
 * flavour without one of the steps from navigating into a gap.
 */
const steps = computed<StepKind[]>(() => {
  const kinds: StepKind[] = ['save-host', 'install', 'register']
  if (props.isPushMode) {
    kinds.push('test-connection')
  }
  return kinds
})

/** 1-based position of a step, or 0 when this flavour does not show it. */
const positionOf = (kind: StepKind): number => steps.value.indexOf(kind) + 1
const isPast = (kind: StepKind): boolean =>
  positionOf(kind) !== 0 && currentStep.value > positionOf(kind)
const isActive = (kind: StepKind): boolean => currentStep.value === positionOf(kind)
const isLast = (kind: StepKind): boolean => positionOf(kind) === steps.value.length

function initialStep(): number {
  if (props.saveHost) {
    return positionOf('save-host')
  }
  if (!props.agentInstalled && positionOf('install')) {
    return positionOf('install')
  }
  return positionOf('register') || 1
}

const currentStep = ref(initialStep())

/** Keep the selection on a step that exists; `CmkWizard` does not clamp. */
watch(steps, (kinds) => {
  currentStep.value = Math.min(Math.max(currentStep.value, 1), kinds.length)
})

const defaultPackageId = (): string => props.tab.subTabs?.[0]?.id ?? ''
const packageId = ref(props.restoredPackageId ?? defaultPackageId())

/** The download token. */
const ott = ref<string | null | Error>(null)
watch(packageId, () => {
  ott.value = null
})
</script>

<template>
  <CmkToggleButtonGroup
    v-if="tab.subTabs && tab.subTabs.length > 1"
    v-model="packageId"
    :options="tab.subTabs.map((st) => ({ label: st.label, value: st.id }))"
  />
  <CmkWizard v-model="currentStep" mode="guided">
    <template v-for="(kind, position) in steps" :key="kind">
      <SaveHostStep
        v-if="kind === 'save-host'"
        :index="position + 1"
        :is-completed="() => isPast('save-host') || !saveHost"
        :is-active="isActive('save-host')"
        :host-name="hostName"
        :save-host="saveHost"
        :host-exists="hostExists"
        :setup-error="setupError"
        @save-host="emit('saveHost', packageId)"
        @close="emit('close')"
      />

      <InstallAgentStep
        v-else-if="kind === 'install'"
        v-model:ott="ott"
        v-model:selected-variant-id="shellId"
        v-model:package-id="packageId"
        :index="position + 1"
        :is-completed="() => isPast('install') || agentInstalled"
        :is-active="isActive('install')"
        :tab="tab"
        :site-id="siteId"
      />

      <RegisterAgent
        v-else-if="kind === 'register'"
        v-model:selected-variant-id="shellId"
        :index="position + 1"
        :is-completed="() => isPast('register')"
        :is-active="isActive('register')"
        :tab="tab"
        :is-last-step="isLast('register')"
        :close-button-title="closeButtonTitle"
        :host-name="hostName"
        :site-id="siteId"
        :user-settings-url="userSettingsUrl"
        :agent-receiver-port-is-default="agentReceiverPortIsDefault"
        @close="emit('close')"
      />

      <TestConnectionStep
        v-else-if="kind === 'test-connection'"
        v-model:selected-variant-id="shellId"
        :index="position + 1"
        :is-completed="() => isPast('test-connection')"
        :is-active="isActive('test-connection')"
        :tab="tab"
        :close-button-title="closeButtonTitle"
        @close="emit('close')"
      />
    </template>
  </CmkWizard>
</template>
