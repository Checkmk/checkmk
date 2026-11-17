<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type AgentSlideout } from 'cmk-shared-typing/typescript/agent_slideout'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import usePersistentRef from 'cmk-ui-library/lib/usePersistentRef'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { TooltipArrow } from 'reka-ui'
import { computed, onBeforeUnmount, onMounted, ref, watchEffect } from 'vue'

import AgentSlideOutContent from '@/mode-host/agent-connection-test/components/AgentSlideOutContent.vue'

interface Props {
  userId: string
  dialogTitle: TranslatedString
  dialogMessage: TranslatedString
  slideInTitle: TranslatedString
  slideInButtonTitle: TranslatedString
  hideButtonTitle: TranslatedString
  closeButtonTitle: TranslatedString
  agentSlideout: AgentSlideout
  isNotRegistered: boolean
  noTlsProvided: boolean
  isPushMode: boolean
  siteId: string
  siteServer: string
  agentReceiverPort: number
  agentReceiverPortIsDefault: boolean
}

const props = defineProps<Props>()

const slideInOpen = ref(false)

const MIN_HINT_WIDTH_PX = 300
const MAX_TABLE_SHARE = 2 / 3

const contentArea = ref(document.getElementById('content_area'))
const messageContainer = ref(
  document.querySelector<HTMLElement>('#datasources_container .message_container')
)
const triggerEl = ref<HTMLElement | null>(null)
const hintEl = ref<HTMLElement | null>(null)

const freeWidth = ref(Infinity)
const hintBottom = ref(0)

function measure() {
  const trigger = triggerEl.value
  const table = trigger?.closest('table')
  if (!contentArea.value || !messageContainer.value || !trigger || !table) {
    return
  }
  const containerRect = messageContainer.value.getBoundingClientRect()
  const widestTableRight =
    table.getBoundingClientRect().left + containerRect.width * MAX_TABLE_SHARE
  freeWidth.value = contentArea.value.getBoundingClientRect().right - widestTableRight
  hintBottom.value = hintEl.value
    ? trigger.getBoundingClientRect().top -
      containerRect.top +
      hintEl.value.getBoundingClientRect().height
    : 0
}

const { observe } = useResizeObserver(measure)
observe(contentArea)
observe(messageContainer)
observe(hintEl)
onMounted(measure)

const localStorageKey = `service-discovery-${props.userId}-${props.agentSlideout.host_name}-hidden`
const tooltipHidden = usePersistentRef(localStorageKey, false, (v) => v as boolean)

const besideRows = computed(() => !messageContainer.value || freeWidth.value >= MIN_HINT_WIDTH_PX)
const tooltipOpen = computed(() => !tooltipHidden.value && !slideInOpen.value && besideRows.value)
const inlineOpen = computed(() => !tooltipHidden.value && !besideRows.value)

watchEffect(() => {
  if (messageContainer.value) {
    messageContainer.value.style.minHeight =
      tooltipOpen.value && hintBottom.value ? `${hintBottom.value}px` : ''
  }
})
onBeforeUnmount(() => messageContainer.value?.style.removeProperty('min-height'))

const alertProps = computed(() => ({
  heading: props.dialogTitle,
  text: props.dialogMessage,
  variant: 'info' as const,
  mainButton: {
    title: props.slideInButtonTitle,
    onclick: () => {
      slideInOpen.value = true
    }
  },
  optionalButton: {
    title: props.hideButtonTitle,
    icon: 'cancel' as const,
    onclick: () => {
      tooltipHidden.value = true
    }
  }
}))

// The rescan button always contains the current js call with all needed
// params. Solution is not the best but without VUE on the setup page we have
// limited options to solve this.
const triggerRescan = () => {
  const rescanElement = [...document.querySelectorAll('a')].find(
    (a) => a.textContent.trim() === 'Rescan'
  ) as HTMLAnchorElement | null | undefined
  rescanElement?.click()
}
</script>

<template>
  <CmkTooltipProvider>
    <CmkTooltip :open="tooltipOpen" class="tooltip">
      <CmkTooltipTrigger as-child>
        <span
          ref="triggerEl"
          class="setup-agent-download-dialog__trigger"
          :data-agent-hint="tooltipOpen ? 'open' : undefined"
        ></span>
      </CmkTooltipTrigger>
      <CmkTooltipContent
        variant="unstyled"
        align="start"
        side="right"
        :side-offset="0"
        :avoid-collisions="false"
        :collision-boundary="contentArea"
        :use-portal="true"
        class="setup-agent-download-dialog__tooltip-content"
      >
        <TooltipArrow
          :style="{ fill: 'var(--cmk-alert-box-info-bg-color)' }"
          :width="16"
          :height="8"
        />
        <div ref="hintEl">
          <CmkAlert v-bind="alertProps" class="setup-agent-download-dialog__alert" />
        </div>
      </CmkTooltipContent>
    </CmkTooltip>
  </CmkTooltipProvider>
  <Teleport v-if="inlineOpen && messageContainer" :to="messageContainer">
    <CmkAlert v-bind="alertProps" class="setup-agent-download-dialog__inline-alert" />
  </Teleport>
  <CmkSlideInDialog
    :open="slideInOpen"
    :header="{ title: slideInTitle, closeButton: true }"
    @close="slideInOpen = false"
  >
    <AgentSlideOutContent
      :all-agents-url="agentSlideout.all_agents_url"
      :user-settings-url="agentSlideout.user_settings_url"
      :host-name="agentSlideout.host_name"
      :site-id="siteId"
      :site-server="siteServer"
      :agent-receiver-port="agentReceiverPort"
      :agent-receiver-port-is-default="agentReceiverPortIsDefault"
      :agent-install-cmds="agentSlideout.agent_install_cmds"
      :agent-registration-cmds="agentSlideout.agent_registration_cmds"
      :agent-status-cmds="agentSlideout.agent_status_cmds"
      :command-placeholders="agentSlideout.command_placeholders"
      :legacy-agent-url="agentSlideout.legacy_agent_url"
      :kubernetes-helm-command="agentSlideout.kubernetes_helm_command"
      :kubernetes-values="agentSlideout.kubernetes_values"
      :kubernetes-doc-url="agentSlideout.kubernetes_doc_url"
      :close-button-title="closeButtonTitle"
      :save-host="agentSlideout.save_host"
      :host-exists="agentSlideout.host_exists ?? false"
      :setup-error="false"
      :agent-installed="isNotRegistered"
      :is-push-mode="isPushMode"
      :unbaked-fallback="agentSlideout.unbaked_fallback ?? null"
      :bakery-url="agentSlideout.bakery_url"
      @close="((slideInOpen = false), (tooltipHidden = true), triggerRescan())"
    />
  </CmkSlideInDialog>
</template>

<style scoped>
.setup-agent-download-dialog__trigger {
  display: inline-block;
  width: 0;
  height: 1em;
  vertical-align: middle;
}

.setup-agent-download-dialog__tooltip-content {
  max-width: var(--reka-tooltip-content-available-width);
}

/* Start at the arrow, not below it */
.setup-agent-download-dialog__tooltip-content .setup-agent-download-dialog__alert {
  margin: 0;
}
</style>

<style>
/* Unscoped, portal -> body */
.setup-agent-download-dialog__tooltip-content {
  z-index: var(--z-index-modal);
  max-width: var(--reka-tooltip-content-available-width);
}
</style>
