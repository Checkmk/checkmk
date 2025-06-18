<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import type { Ref } from 'vue'
import CmkButton from '@/components/CmkButton.vue'
import SlideIn from '@/components/SlideIn.vue'
import CmkIcon from '@/components/CmkIcon.vue'

interface Props {
  url: string
  dialog_message: string
  slide_in_title: string
  msg_start: string
  msg_success: string
  msg_loading: string
  msg_missing: string
  msg_error: string
  input_hostname: string
  input_ipv4: string
  input_ipv6: string
}

const props = defineProps<Props>()

const slideInOpen = ref(false)
const externalContent = ref('')

const hostname = ref('')
const ipV4 = ref('')
const ipV6 = ref('')
onMounted(() => {
  // Add ipaddress validation
  function watchInput(name: string, targetRef: Ref<string>) {
    const input = document.querySelector(`[name="${name}"]`) as HTMLInputElement | null
    if (!input) {
      return
    }

    targetRef.value = input.value

    input.addEventListener('input', () => {
      targetRef.value = input.value
      isLoading.value = false
      isSuccess.value = false
      isError.value = false
    })
  }

  watchInput(props.input_hostname, hostname)
  watchInput(props.input_ipv4, ipV4)
  watchInput(props.input_ipv6, ipV6)
})

const isLoading = ref(false)
const isSuccess = ref(false)
const isError = ref(false)
const errorDetails = ref('')
const tooltipText = computed(() => {
  if (isLoading.value) {
    return props.msg_loading
  }
  if (isSuccess.value) {
    return props.msg_success
  }
  if (isError.value) {
    return props.msg_error
  }
  if (!hostname.value) {
    return props.msg_missing
  }
  return props.msg_start
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

// Add observer
const getCurrentAddressFamily = () => {
  const dropdownChoices = document.querySelector('#attr_entry_tag_address_family') as HTMLElement
  if (dropdownChoices && dropdownChoices.offsetParent !== null) {
    const selected = dropdownChoices.querySelector('select')
    if (selected) {
      return selected.value
    }
  }

  const defaultChoice = document.querySelector('#attr_default_tag_address_family') as HTMLElement
  if (defaultChoice && defaultChoice.offsetParent !== null) {
    const defaultValue = defaultChoice.querySelector('b')
    if (defaultValue) {
      return defaultValue.textContent?.trim()
    }
  }

  return 'ip-v4-only'
}

async function callAjax(url: string, { method }: AjaxOptions): Promise<void> {
  try {
    const siteIdDefaultValue = document.getElementById('attr_default_site')
    const siteIdDropdownValue = document.getElementById('attr_entry_site')
    const siteId = ref('')
    if (siteIdDefaultValue && siteIdDropdownValue) {
      const siteIdDefaultValueVisibility = siteIdDefaultValue.getAttribute('style')
      if (!siteIdDefaultValueVisibility) {
        siteId.value = siteIdDefaultValue.textContent ?? ''
      } else {
        siteId.value = siteIdDropdownValue.textContent ?? ''
      }
    }

    const postDataRaw = new URLSearchParams({
      host_name: hostname.value ?? '',
      ipaddress: ipV4.value ?? ipV6.value ?? '',
      address_family: getCurrentAddressFamily() ?? 'ip-v4-only',
      agent_port: '6556',
      timeout: '5',
      site_id: siteId.value.split(' - ')[0] ?? ''
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

  <!-- eslint-disable vue/no-bare-strings-in-template -->
  <CmkButton
    v-if="errorDetails.includes('[Errno 111]')"
    type="button"
    title="Download agent"
    @click="slideInOpen = true"
  >
    Download Checkmk agent
  </CmkButton>
  <!-- eslint-enable vue/no-bare-strings-in-template -->
  <span v-if="isError && !errorDetails.includes('[Errno 111]')" class="error_msg">
    {{ errorDetails }}
  </span>
  <SlideIn
    :open="slideInOpen"
    :header="{ title: slide_in_title, closeButton: true }"
    @close="slideInOpen = false"
  >
    <!-- eslint-disable-next-line vue/no-bare-strings-in-template -->
    <div>Error: {{ errorDetails }}</div>
    <!-- eslint-disable-next-line vue/no-v-html -->
    <div v-html="externalContent"></div>
  </SlideIn>
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
