<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkWizard from 'cmk-ui-library/components/CmkWizard'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref, watch } from 'vue'

import type { HostMacros, TokenValue } from '../lib/commandTemplate'
import type { AgentFlavour } from '../lib/types'
import ShellToggle from './ShellToggle.vue'
import InstallAgentStep from './steps/InstallAgentStep.vue'
import RegisterAgent from './steps/RegisterAgent.vue'
import SaveHostStep from './steps/SaveHostStep.vue'
import TestConnectionStep from './steps/TestConnectionStep.vue'

const props = defineProps<{
  flavour: AgentFlavour
  macros: HostMacros
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
  const kinds: StepKind[] = ['save-host']
  if (props.flavour.install) {
    kinds.push('install')
  }
  if (props.flavour.register) {
    kinds.push('register')
  }
  if (props.isPushMode && props.flavour.status) {
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

/** The package choices, when this flavour installs from one of several packages. */
const packageChoices = computed(() =>
  props.flavour.install?.kind === 'package-choice' ? props.flavour.install.choices : null
)

const packageId = ref(props.restoredPackageId ?? packageChoices.value?.[0]?.id ?? '')

/** The download token. */
const ott = ref<TokenValue>(null)
watch(packageId, () => {
  ott.value = null
})
</script>

<template>
  <ShellToggle v-if="packageChoices" v-model="packageId" :choices="packageChoices" />
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
        v-else-if="kind === 'install' && flavour.install"
        v-model:ott="ott"
        v-model:shell-id="shellId"
        v-model:package-id="packageId"
        :index="position + 1"
        :is-completed="() => isPast('install') || agentInstalled"
        :is-active="isActive('install')"
        :spec="flavour.install"
        :macros="macros"
        :site-id="siteId"
      />

      <RegisterAgent
        v-else-if="kind === 'register' && flavour.register"
        v-model:shell-id="shellId"
        :index="position + 1"
        :is-completed="() => isPast('register')"
        :is-active="isActive('register')"
        :spec="flavour.register"
        :macros="macros"
        :is-last-step="isLast('register')"
        :close-button-title="closeButtonTitle"
        :host-name="hostName"
        :site-id="siteId"
        :user-settings-url="userSettingsUrl"
        :agent-receiver-port-is-default="agentReceiverPortIsDefault"
        @close="emit('close')"
      />

      <TestConnectionStep
        v-else-if="kind === 'test-connection' && flavour.status"
        v-model:shell-id="shellId"
        :index="position + 1"
        :is-completed="() => isPast('test-connection')"
        :is-active="isActive('test-connection')"
        :spec="flavour.status"
        :macros="macros"
        :close-button-title="closeButtonTitle"
        @close="emit('close')"
      />
    </template>
  </CmkWizard>
</template>
