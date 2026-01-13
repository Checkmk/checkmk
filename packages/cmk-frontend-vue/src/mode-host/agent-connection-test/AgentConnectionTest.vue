<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type AgentSlideout } from 'cmk-shared-typing/typescript/agent_slideout'
import {
  type ModeHostAgentConnectionMode,
  type ModeHostServerPerSite,
  type ModeHostSite
} from 'cmk-shared-typing/typescript/mode_host'
import type { Ref } from 'vue'
import { computed, onMounted, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'

import AgentSlideOutContent from '@/mode-host/agent-connection-test/components/AgentSlideOutContent.vue'

defineOptions({
  inheritAttrs: false
})

const { _t } = usei18n()

interface Props {
  formElement: HTMLFormElement
  changeTagAgent: HTMLInputElement
  tagAgent: HTMLSelectElement
  tagAgentDefault: HTMLDivElement
  hostnameInputElement: HTMLInputElement
  ipv4InputElement: HTMLInputElement
  ipv4InputButtonElement: HTMLInputElement
  ipv6InputElement: HTMLInputElement
  ipv6InputButtonElement: HTMLInputElement
  siteSelectElement: HTMLSelectElement
  ipAddressFamilySelectElement: HTMLSelectElement
  ipAddressFamilyInputElement: HTMLInputElement
  cmkAgentConnectionModeSelectElement: HTMLSelectElement | null
  sites: Array<ModeHostSite>
  serverPerSite: Array<ModeHostServerPerSite>
  agentConnectionModes: Array<ModeHostAgentConnectionMode>
  agentSlideout: AgentSlideout
  setupError: boolean
}

const props = defineProps<Props>()

const slideInOpen = ref(false)

const showTest = ref(true)
const isPushMode = ref(false)
const switchVisibility = () => {
  showTest.value = true
  if (
    props.ipAddressFamilyInputElement.checked &&
    props.ipAddressFamilySelectElement.value === 'no-ip'
  ) {
    showTest.value = false
    return
  }

  if (props.ipAddressFamilyInputElement.checked && props.ipAddressFamilySelectElement.value) {
    isLoading.value = false
    isSuccess.value = false
    isError.value = false
    if (props.setupError) {
      setupErrorActive.value = false
    }
    ipV6.value = ''
    ipV4.value = ''
  }

  if (props.changeTagAgent.checked) {
    showTest.value = props.tagAgent.value === 'all-agents' || props.tagAgent.value === 'cmk-agent'
    return
  }
  /* TODO: Not the best solution but we have no value here */
  showTest.value = !props.tagAgentDefault.textContent?.includes('no Checkmk agent')
}
switchVisibility()
checkPushMode()

function checkPushMode() {
  const agentConnectionModeHash = props.cmkAgentConnectionModeSelectElement?.value
  const agentConnectionMode =
    props.agentConnectionModes.find((mode) => mode.id_hash === agentConnectionModeHash)?.mode ?? ''
  isPushMode.value = agentConnectionMode === 'push-agent'
}

const hostname = ref(props.hostnameInputElement.value || '')
const ipV4Selected = ref(false)
const ipV6Selected = ref(false)
const selectedSiteIdHash = ref(props.siteSelectElement.value)
const siteId = ref(
  props.sites.find((site) => site.id_hash === selectedSiteIdHash.value)?.site_id ?? ''
)
const siteServer = ref(
  props.serverPerSite.find((item) => item.site_id === siteId.value)?.server ?? ''
)
const ipV4 = ref(props.ipv4InputElement.value || '')
const ipV6 = ref(props.ipv6InputElement.value || '')
const targetElement = ref<HTMLElement>(
  props.changeTagAgent.checked ? (props.tagAgent.parentNode as HTMLElement) : props.tagAgentDefault
)
const setupErrorActive = ref(props.setupError)

onMounted(() => {
  ipV4Selected.value = props.ipv4InputButtonElement.checked
  ipV6Selected.value = props.ipv6InputButtonElement.checked
  selectedSiteIdHash.value = props.siteSelectElement.value
  siteId.value =
    props.sites.find((site) => site.id_hash === selectedSiteIdHash.value)?.site_id ?? ''
  siteServer.value = props.serverPerSite.find((item) => item.site_id === siteId.value)?.server ?? ''

  if (sessionStorage.getItem('reopenSlideIn') === 'true') {
    void startAjax().then(() => {
      if (!props.setupError) {
        slideInOpen.value = true
      }
      sessionStorage.removeItem('reopenSlideIn')
    })
  }
  props.formElement.addEventListener('change', (e: Event) => {
    switch (e.target) {
      case props.formElement:
      case props.changeTagAgent: {
        switchVisibility()
        checkPushMode()

        targetElement.value = props.changeTagAgent.checked
          ? (props.tagAgent.parentNode as HTMLElement)
          : props.tagAgentDefault
        break
      }
      case props.siteSelectElement: {
        selectedSiteIdHash.value = props.siteSelectElement.value
        siteId.value =
          props.sites.find((site) => site.id_hash === selectedSiteIdHash.value)?.site_id ?? ''
        siteServer.value =
          props.serverPerSite.find((item) => item.site_id === siteId.value)?.server ?? ''
        break
      }
      case props.ipv4InputButtonElement: {
        if (!ipV4Selected.value) {
          ipV4.value = ''
        }
        break
      }
      case props.ipv6InputButtonElement: {
        if (!ipV6Selected.value) {
          ipV6.value = ''
        }
        break
      }
    }
  })
  // Add ipaddress validation
  function watchInput(input: HTMLInputElement, targetRef: Ref<string>) {
    input.addEventListener('input', () => {
      targetRef.value = input.value
      isLoading.value = false
      isSuccess.value = false
      isError.value = false
      if (props.setupError) {
        setupErrorActive.value = false
      }
    })
  }

  function watchCheckbox(
    checkbox: HTMLInputElement,
    checkboxRef: Ref<boolean>,
    valueRef: Ref<string>,
    inputElement: HTMLInputElement
  ) {
    checkbox.addEventListener('change', () => {
      checkboxRef.value = checkbox.checked

      if (checkbox.checked) {
        valueRef.value = inputElement.value
      }

      isLoading.value = false
      isSuccess.value = false
      isError.value = false
      if (props.setupError) {
        setupErrorActive.value = false
      }
    })
  }

  watchInput(props.hostnameInputElement, hostname)
  watchInput(props.ipv4InputElement, ipV4)
  watchInput(props.ipv6InputElement, ipV6)
  watchCheckbox(props.ipv4InputButtonElement, ipV4Selected, ipV4, props.ipv4InputElement)
  watchCheckbox(props.ipv6InputButtonElement, ipV6Selected, ipV6, props.ipv6InputElement)
})

const isLoading = ref(false)
const isSuccess = ref(false)
const isError = ref(false)
const errorDetails = ref('')
const tooltipText = computed(() => {
  if (isLoading.value) {
    return _t('Agent connection test running')
  }
  if (isSuccess.value) {
    return _t('Agent connection successful')
  }
  if (isError.value) {
    return _t(
      'Connection failed, enter new hostname to check again or download and install the Checkmk agent.'
    )
  }
  if (!hostname.value) {
    return _t('Please enter a hostname to test Checkmk agent connection')
  }
  return _t('Test Checkmk agent connection')
})
const isNotRegistered = computed(() => {
  if (errorDetails.value.includes('controller not registered')) {
    return true
  }
  return false
})

const slideOutTitle = computed(() => {
  if (isNotRegistered.value) {
    return _t('Register agent')
  }
  return _t('Install Checkmk agent')
})

type AutomationResponse = {
  output: string
  status_code: number
}

type AjaxResponse = {
  result_code: number
  result?: AutomationResponse
}

type AjaxOptions = {
  method: 'POST' | 'GET'
}

async function callAjax(url: string, { method }: AjaxOptions): Promise<void> {
  try {
    const siteIdHash = props.siteSelectElement.value
    const siteIdent = props.sites.find((site) => site.id_hash === siteIdHash)?.site_id ?? ''
    const postDataRaw = new URLSearchParams({
      host_name: hostname.value || '',
      ipaddress: ipV4.value || ipV6.value || '',
      address_family: props.ipAddressFamilySelectElement.value ?? 'ip-v4-only',
      agent_port: '6556',
      timeout: '5',
      site_id: siteIdent
    })

    const postData = postDataRaw.toString()

    isLoading.value = true
    isError.value = false
    isSuccess.value = false

    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: postData
    })

    if (!res.ok) {
      throw new Error(`Error: ${res.status}`)
    }

    const data: AjaxResponse = await res.json()

    if (data.result?.status_code === 0) {
      isSuccess.value = true
    } else {
      isError.value = true
      errorDetails.value = data.result?.output ?? ''
    }
  } catch (err) {
    console.error('Error:', err)
    isError.value = true
  } finally {
    isLoading.value = false
  }
}

// Use general way for AjaxCalls if available
const startAjax = (): Promise<void> => {
  isSuccess.value = false
  isError.value = false

  return callAjax('wato_ajax_diag_cmk_agent.py', {
    method: 'POST'
  })
}

const reTestAgentTitle = _t('Re-test agent connection')
const reTestAgentButton = _t('Re-test agent connection')
const reTestAgentClick: () => Promise<void> = startAjax
const openSlideoutClick: () => void = () => {
  slideInOpen.value = true
}

interface ContainerValues {
  header: string
  txt: string
  buttonOneTitle: string
  buttonOneButton: string
  buttonOneClick: () => void | Promise<void>
  buttonTwoTitle: string
  buttonTwoButton: string
  buttonTwoClick: () => void | Promise<void>
}

const warnContainerValues = computed<ContainerValues>(() => {
  let header = _t('Agent connection failed')
  let txt = errorDetails.value
  let buttonOneTitle = reTestAgentTitle
  let buttonOneButton = reTestAgentButton
  let buttonOneClick: () => void | Promise<void> = reTestAgentClick
  let buttonTwoTitle = ''
  let buttonTwoButton = ''
  let buttonTwoClick: () => void | Promise<void> = () => {}

  if (errorDetails.value.includes('[Errno 111]')) {
    header = _t('Failed to connect to the Checkmk agent')
    txt = _t('This may be because the agent is not installed or not running on the target system.')
    buttonOneTitle = _t('Download & install agent')
    buttonOneButton = _t('Download Checkmk agent')
    buttonOneClick = openSlideoutClick
    buttonTwoTitle = reTestAgentTitle
    buttonTwoButton = reTestAgentButton
    buttonTwoClick = reTestAgentClick
  }
  if (isNotRegistered.value) {
    header = _t('Agent not registered')
    txt = _t('The agent has been installed on the target system but has not yet been registered.')
    buttonOneTitle = _t('Register agent')
    buttonOneButton = _t('Register Checkmk agent')
    buttonOneClick = openSlideoutClick
    buttonTwoTitle = reTestAgentTitle
    buttonTwoButton = reTestAgentButton
    buttonTwoClick = reTestAgentClick
  }
  if (errorDetails.value.includes('is not providing it')) {
    header = _t('TLS connection not provided')
    txt = _t(
      'The agent has been installed on the target system but is not providing a TLS connection.'
    )
    buttonOneTitle = _t('Provide TLS connection')
    buttonOneButton = _t('Provide TLS connection')
    buttonOneClick = openSlideoutClick
    buttonTwoTitle = reTestAgentTitle
    buttonTwoButton = reTestAgentButton
    buttonTwoClick = reTestAgentClick
  }

  return {
    header,
    txt,
    buttonOneTitle,
    buttonOneButton,
    buttonOneClick,
    buttonTwoTitle,
    buttonTwoButton,
    buttonTwoClick
  }
})

function onClose() {
  slideInOpen.value = false
  isError.value = false
  if (!isPushMode.value) {
    void startAjax()
  }
}
</script>

<template>
  <Teleport v-if="showTest" :to="targetElement">
    <CmkButton
      v-if="!isLoading && !isSuccess && !isError"
      type="button"
      :title="tooltipText"
      class="agent-test-button"
      :disabled="!hostname && !ipV4 && !ipV6"
      @click="startAjax"
    >
      <CmkIcon name="connection-tests" size="small" :title="tooltipText" class="button-icon" />
      {{ _t('Test agent connection') }}
    </CmkButton>

    <CmkAlertBox v-if="isLoading" variant="loading" size="small" class="loading-container">
      {{ _t('Testing agent connection ...') }}
    </CmkAlertBox>

    <CmkAlertBox v-if="isSuccess" variant="success" size="small" class="success-container">
      {{ _t('Successfully connected to agent.') }}
      <a href="#" @click.prevent="startAjax">{{ _t('Re-test agent connection') }}</a>
    </CmkAlertBox>

    <CmkAlertBox v-if="isError" variant="warning" size="small" class="warn-container">
      <template #heading>{{ warnContainerValues.header }}</template>
      <div class="warn-txt-container">
        {{ warnContainerValues.txt }}
        <div class="warn-button-container">
          <CmkButton
            type="button"
            :title="warnContainerValues.buttonOneTitle"
            class="agent-test-button alert-box-button"
            @click="warnContainerValues.buttonOneClick"
          >
            {{ warnContainerValues.buttonOneButton }}
          </CmkButton>
          <CmkButton
            v-if="warnContainerValues.buttonTwoTitle"
            type="button"
            :title="warnContainerValues.buttonTwoTitle"
            class="agent-test-button alert-box-button"
            @click="warnContainerValues.buttonTwoClick"
          >
            {{ warnContainerValues.buttonTwoButton }}
          </CmkButton>
        </div>
      </div>
    </CmkAlertBox>

    <CmkSlideInDialog
      :header="{
        title: slideOutTitle,
        closeButton: true
      }"
      :open="slideInOpen"
      @close="slideInOpen = false"
    >
      <AgentSlideOutContent
        :all-agents-url="agentSlideout.all_agents_url"
        :host-name="hostname"
        :site-id="siteId"
        :site-server="siteServer"
        :agent-install-cmds="agentSlideout.agent_install_cmds"
        :agent-registration-cmds="agentSlideout.agent_registration_cmds"
        :legacy-agent-url="agentSlideout.legacy_agent_url"
        :save-host="agentSlideout.save_host"
        :host-exists="agentSlideout.host_exists ?? false"
        :setup-error="setupErrorActive"
        :close-button-title="isPushMode ? _t('Close slideout') : _t('Close & test connection')"
        :agent-installed="isNotRegistered"
        :is-push-mode="isPushMode"
        @close="onClose"
      />
    </CmkSlideInDialog>
  </Teleport>
</template>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */

button {
  border: none;
  margin: 0;
  padding: 0;

  .button-icon {
    margin-right: var(--spacing-half);
  }
}

.agent-test-button {
  margin-left: var(--spacing-half);
  height: 21px;

  &.alert-box-button {
    margin-left: 0;
    margin-right: var(--spacing-half);
  }
}

.warn-container,
.loading-container,
.success-container {
  display: inline-flex;
  color: var(--font-color);
  margin: 0 0 0 var(--dimension-4);
}

.warn-container {
  padding: var(--dimension-4) var(--dimension-5);

  .warn-txt-container {
    display: inline-flex;
    flex-direction: column;
  }

  .warn-button-container {
    margin: var(--spacing-half) 0 0;
  }
}
</style>
