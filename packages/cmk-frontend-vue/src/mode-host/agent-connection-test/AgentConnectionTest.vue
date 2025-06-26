<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import type { Ref } from 'vue'
import usei18n from '@/lib/i18n'
import CmkButton from '@/components/CmkButton.vue'
import SlideIn from '@/components/SlideIn.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import { type I18NAgentConnection, type ModeHostSite } from 'cmk-shared-typing/typescript/mode_host'

const { t } = usei18n('agent_connection_test')

interface Props {
  formElement: HTMLFormElement
  changeTagAgent: HTMLInputElement
  tagAgent: HTMLSelectElement
  tagAgentDefault: HTMLDivElement
  hostnameInputElement: HTMLInputElement
  ipv4InputElement: HTMLInputElement
  ipv6InputElement: HTMLInputElement
  siteSelectElement: HTMLSelectElement
  ipAddressFamilySelectElement: HTMLSelectElement
  i18n: I18NAgentConnection
  sites: Array<ModeHostSite>
  url: string
}

const props = defineProps<Props>()

const slideInOpen = ref(false)
const externalContent = ref('')

const showTest = ref(true)
const switchVisibility = () => {
  if (props.changeTagAgent.checked) {
    showTest.value = props.tagAgent.value === 'all-agents' || props.tagAgent.value === 'cmk-agent'
  } else {
    /* TODO: Not the best solution but we have no value here */
    showTest.value = !props.tagAgentDefault.textContent?.includes('no Checkmk agent')
  }
}
switchVisibility()

const hostname = ref(props.hostnameInputElement.value || '')
const ipV4 = ref(props.ipv4InputElement.value || '')
const ipV6 = ref(props.ipv6InputElement.value || '')
const targetElement = ref<HTMLElement>(
  props.changeTagAgent.checked ? (props.tagAgent.parentNode as HTMLElement) : props.tagAgentDefault
)

onMounted(() => {
  props.formElement.addEventListener('change', (e: Event) => {
    switch (e.target) {
      case props.formElement:
      case props.changeTagAgent: {
        switchVisibility()

        targetElement.value = props.changeTagAgent.checked
          ? (props.tagAgent.parentNode as HTMLElement)
          : props.tagAgentDefault
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
    })
  }

  watchInput(props.hostnameInputElement, hostname)
  watchInput(props.ipv4InputElement, ipV4)
  watchInput(props.ipv6InputElement, ipV6)
})

const isLoading = ref(false)
const isSuccess = ref(false)
const isError = ref(false)
const errorDetails = ref('')
const tooltipText = computed(() => {
  if (isLoading.value) {
    return props.i18n.msg_loading
  }
  if (isSuccess.value) {
    return props.i18n.msg_success
  }
  if (isError.value) {
    return props.i18n.msg_error
  }
  if (!hostname.value) {
    return props.i18n.msg_missing
  }
  return props.i18n.msg_start
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
    const siteId = props.sites.find((site) => site.id_hash === siteIdHash)?.site_id ?? ''
    const postDataRaw = new URLSearchParams({
      host_name: hostname.value ?? '',
      ipaddress: ipV4.value ?? ipV6.value ?? '',
      address_family: props.ipAddressFamilySelectElement.value ?? 'ip-v4-only',
      agent_port: '6556',
      timeout: '5',
      site_id: siteId
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
const startAjax = (): void => {
  isSuccess.value = false
  isError.value = false

  void callAjax('wato_ajax_diag_cmk_agent.py', {
    method: 'POST'
  })
}

const reTestAgentTitle = t('re-test-agent-title', 'Re-test agent connection')
const reTestAgentButton = t('re-test-agent-button', 'Re-test agent connection')
const reTestAgentClick: () => void = startAjax
const openSlideoutClick: () => void = () => {
  slideInOpen.value = true
}

interface ContainerValues {
  header: string
  txt: string
  buttonOneTitle: string
  buttonOneButton: string
  buttonOneClick: () => void
  buttonTwoTitle: string
  buttonTwoButton: string
  buttonTwoClick: () => void
}

const warnContainerValues = computed<ContainerValues>(() => {
  let header = t('test-agent-general-header', 'Agent connection failed')
  let txt = errorDetails.value
  let buttonOneTitle = reTestAgentTitle
  let buttonOneButton = reTestAgentButton
  let buttonOneClick = reTestAgentClick
  let buttonTwoTitle = ''
  let buttonTwoButton = ''
  let buttonTwoClick = () => {}

  if (errorDetails.value.includes('[Errno 111]')) {
    header = t('test-agent-warning-header', 'Failed to connect to the Checkmk agent')
    txt = t(
      'test-agent-warning-msg',
      'This may be because the agent is not installed or not running on the target system.'
    )
    buttonOneTitle = t('download-agent-title', 'Download % install agent')
    buttonOneButton = t('download-agent-button', 'Download Checkmk agent')
    buttonOneClick = openSlideoutClick
    buttonTwoTitle = reTestAgentTitle
    buttonTwoButton = reTestAgentButton
    buttonTwoClick = reTestAgentClick
  }
  if (errorDetails.value.includes('controller not registered')) {
    header = t('test-agent-not-registered-header', 'Agent not registered')
    txt = t(
      'test-agent-not-registered-msg',
      'The agent has been installed on the target system but has not yet been registered.'
    )
    buttonOneTitle = t('register-agent-title', 'Register agent')
    buttonOneButton = t('register-agent-button', 'Register Checkmk agent')
    buttonOneClick = openSlideoutClick
    buttonTwoTitle = reTestAgentTitle
    buttonTwoButton = reTestAgentButton
    buttonTwoClick = reTestAgentClick
  }
  if (errorDetails.value.includes('is not providing it')) {
    header = t('test-agent-no-tls-header', 'TLS connection not provided')
    txt = t(
      'test-agent-not-registered-msg',
      'The agent has been installed on the target system but is not providing a TLS connection.'
    )
    buttonOneTitle = t('tls-agent-title', 'Provide TLS connection')
    buttonOneButton = t('tls-agent-button', 'Provide TLS connection')
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
</script>

<template>
  <Teleport v-if="showTest" :to="targetElement">
    <CmkButton
      v-if="!isLoading && !isSuccess && !isError"
      type="button"
      :title="tooltipText"
      class="agent-test-button"
      :disabled="hostname === '' && ipV4 === '' && ipV6 === ''"
      @click="startAjax"
    >
      <CmkIcon name="connection-tests" size="small" :title="tooltipText" class="button-icon" />
      {{ t('msg-start-test', 'Test agent connection') }}
    </CmkButton>

    <div v-if="isLoading" class="loading-container">
      <CmkIcon name="load-graph" :title="tooltipText" size="medium" variant="inline" />
      {{ t('test-agent-loading', 'Testing agent connection ...') }}
    </div>

    <div v-if="isSuccess" class="success-container">
      <CmkIcon name="checkmark" :title="tooltipText" size="medium" variant="inline" />
      {{ t('test-agent-success', 'Successfully connected to agent.') }}
      <a href="#" @click.prevent="startAjax">{{ t('msg-retest', 'Re-test agent connection') }}</a>
    </div>

    <div v-if="isError" class="warn-container">
      <CmkIcon name="validation-error" size="medium" variant="inline" />
      <div class="warn-txt-container">
        <h2>{{ warnContainerValues.header }}</h2>
        <p>{{ warnContainerValues.txt }}</p>
        <div class="warn-button-container">
          <CmkButton
            type="button"
            :title="warnContainerValues.buttonOneTitle"
            class="agent-test-button"
            @click="warnContainerValues.buttonOneClick"
          >
            {{ warnContainerValues.buttonOneButton }}
          </CmkButton>
          <CmkButton
            v-if="warnContainerValues.buttonTwoTitle"
            type="button"
            :title="warnContainerValues.buttonTwoTitle"
            class="agent-test-button"
            @click="warnContainerValues.buttonTwoClick"
          >
            {{ warnContainerValues.buttonTwoButton }}
          </CmkButton>
        </div>
      </div>
    </div>

    <SlideIn
      :open="slideInOpen"
      :header="{ title: i18n.slide_in_title, closeButton: true }"
      @close="slideInOpen = false"
    >
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div v-html="externalContent"></div>
    </SlideIn>
  </Teleport>
</template>

<style scoped>
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
}

.warn-container,
.loading-container,
.success-container {
  display: inline-block;
  padding: 2px 8px;
  vertical-align: top;
  color: var(--font-color);

  /* TODO: Can be removed when CMK-23811 is fixed */
  .cmk-icon {
    display: inline-block;
  }
}

.warn-container {
  border-radius: 4px;
  background-color: rgb(from var(--color-warning) r g b / 15%);

  .warn-txt-container {
    display: inline-block;
    vertical-align: middle;
    margin-top: var(--spacing-half);

    h2,
    p {
      margin: 0 0 0 var(--spacing-half);
    }
  }

  .warn-button-container {
    margin: var(--spacing-half) 0 var(--spacing-half) 0;
  }
}
</style>
