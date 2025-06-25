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

const hostname = ref('')
const ipV4 = ref('')
const ipV6 = ref('')
const targetElement = ref<HTMLElement>(
  props.changeTagAgent.checked ? (props.tagAgent.parentNode as HTMLElement) : props.tagAgentDefault
)

onMounted(() => {
  props.formElement.addEventListener('change', (e: Event) => {
    switch (e.target) {
      case props.formElement:
      case props.changeTagAgent: {
        showTest.value =
          props.tagAgent.value === 'all-agents' || props.tagAgent.value === 'cmk-agent'
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

    if (data.result_code === 0 && data.result && data.result.status_code === 0) {
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
function startAjax(): void {
  isSuccess.value = false
  isError.value = false

  void callAjax('wato_ajax_diag_cmk_agent.py', {
    method: 'POST'
  })
}
</script>

<template>
  <Teleport v-if="showTest" :to="targetElement">
    <CmkButton v-if="isLoading || isSuccess || isError" type="button">
      <CmkIcon
        v-if="isLoading && hostname !== ''"
        name="load-graph"
        size="xlarge"
        :title="tooltipText"
      />

      <CmkIcon
        v-else-if="isSuccess && hostname !== ''"
        name="checkmark"
        size="large"
        :title="tooltipText"
      />
      <CmkIcon v-else-if="isError" name="cross" size="xlarge" :title="tooltipText" />
    </CmkButton>

    <CmkButton
      v-if="!isLoading && !isSuccess && !isError"
      type="button"
      :title="tooltipText"
      :disabled="hostname === '' && ipV4 === '' && ipV6 === ''"
      @click="startAjax"
    >
      <CmkIcon name="start" size="xlarge" :title="tooltipText" />
    </CmkButton>

    <CmkButton
      v-if="errorDetails.includes('[Errno 111]')"
      type="button"
      :title="t('download-agent-title', 'Download agent')"
      @click="slideInOpen = true"
    >
      {{ t('download-agent-button', 'Download Checkmk agent') }}
    </CmkButton>
    <span v-if="isError && !errorDetails.includes('[Errno 111]')" class="error_msg">
      {{ errorDetails }}
    </span>
    <SlideIn
      :open="slideInOpen"
      :header="{ title: i18n.slide_in_title, closeButton: true }"
      @close="slideInOpen = false"
    >
      <div>{{ t('error', 'Error') }}: {{ errorDetails }}</div>
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div v-html="externalContent"></div>
    </SlideIn>
  </Teleport>
</template>

<style scoped>
button {
  background-color: transparent;
  border: none;
  margin: 0;
  padding: 0;

  #error {
    background-color: black;
  }
}

.cmk-button {
  margin-left: var(--spacing);
  height: auto;
  padding: 0;
}

span.error_msg {
  margin-left: var(--spacing);
  color: red;
}
</style>
