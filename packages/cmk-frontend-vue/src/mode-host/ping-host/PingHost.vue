<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import axios from 'axios'
import { type I18NPingHost, type ModeHostSite } from 'cmk-shared-typing/typescript/mode_host'
import { type Ref, computed, onMounted, ref } from 'vue'

import CmkAlertBox, { type Variants } from '@/components/CmkAlertBox.vue'

const props = defineProps<{
  i18n: I18NPingHost
  formElement: HTMLFormElement
  ipAddressFamilySelectElement: HTMLSelectElement
  ipAddressFamilyInputElement: HTMLInputElement
  hostnameInputElement: HTMLInputElement
  ipv4InputElement: HTMLInputElement
  ipv4InputButtonElement: HTMLInputElement
  ipv6InputElement: HTMLInputElement
  ipv6InputButtonElement: HTMLInputElement
  relayInputButtonElement: HTMLInputElement | null
  siteSelectElement: HTMLSelectElement
  sites: Array<ModeHostSite>
}>()

interface PingHostResponseError {
  result_code: 1
  result: string
}

interface PingHostResponseSuccess {
  result_code: 0
  result: {
    status_code: number
    message: string
  }
}

type PingHostResponse = PingHostResponseError | PingHostResponseSuccess

enum PingCmd {
  Ping = 'ping',
  Ping6 = 'ping6'
}

interface Result {
  status: DNSStatus
  element: HTMLInputElement
}

const statusElements: Ref<Record<string, Result>> = ref({})
const isNoIP = ref(
  props.ipAddressFamilyInputElement.checked && props.ipAddressFamilySelectElement.value === 'no-ip'
)
const isRelay = ref(props.relayInputButtonElement?.checked)
const controller = ref(new AbortController())
const ajaxRequestInProgress = ref<{ [key: string]: boolean }>({
  ping: false,
  ping6: false
})

const typingTimer: Ref<{ [key: string]: ReturnType<typeof setTimeout> | null }> = ref({
  ping: null,
  ping6: null
})
const doneTypingInterval = 250

const showPingHost = computed(() => {
  return !isNoIP.value && !isRelay.value
})

onMounted(() => {
  if (props.ipv4InputElement.value) {
    callPingHostOnElement(props.ipv4InputElement, PingCmd.Ping, true)
  }
  if (props.ipv6InputElement.value) {
    callPingHostOnElement(props.ipv6InputElement, PingCmd.Ping6, true)
  }
  props.formElement.addEventListener('change', (e: Event) => {
    switch (e.target) {
      case props.formElement:
        switch (props.ipAddressFamilySelectElement.value) {
          case 'ip-v4-only':
          case 'ip-v6-only':
          case 'ip-v4v6':
            isNoIP.value = false
            break
          case 'no-ip':
            isNoIP.value = true
            statusElements.value = {}
            break
        }
        break
      case props.ipAddressFamilyInputElement:
        isNoIP.value =
          props.ipAddressFamilyInputElement.checked &&
          props.ipAddressFamilySelectElement.value === 'no-ip'
        break
      case props.relayInputButtonElement:
        isRelay.value = props.relayInputButtonElement?.checked
    }
    if (!showPingHost.value) {
      statusElements.value = {}
    }
  })
  props.hostnameInputElement.addEventListener('input', () => {
    if (!showPingHost.value) {
      statusElements.value = {}
      return
    }
    if (props.ipv4InputButtonElement.checked || props.ipv6InputButtonElement.checked) {
      return
    }
    callPingHostOnElement(props.hostnameInputElement, PingCmd.Ping, false)
  })
  props.ipv4InputElement.addEventListener('input', () => {
    if (!showPingHost.value) {
      statusElements.value = {}
      return
    }
    callPingHostOnElement(props.ipv4InputElement, PingCmd.Ping, true)
  })
  props.ipv6InputElement.addEventListener('input', () => {
    if (!showPingHost.value) {
      statusElements.value = {}
      return
    }
    callPingHostOnElement(props.ipv6InputElement, PingCmd.Ping6, true)
  })
})

function callPingHostOnElement(
  element: HTMLInputElement,
  cmd: PingCmd,
  isIpAddress: boolean
): void {
  if (typingTimer.value[cmd]) {
    clearTimeout(typingTimer.value[cmd])
  }
  const elementName = element.name
  if (!elementName) {
    return
  }
  if (!element.value || element.value.trim() === '') {
    delete statusElements.value[elementName]
    return
  }
  if (props.hostnameInputElement.value) {
    delete statusElements.value[props.hostnameInputElement.name]
  }
  statusElements.value[elementName] = {
    status: {
      tooltip: props.i18n.loading,
      status: 'loading'
    },
    element: element
  }
  typingTimer.value[cmd] = setTimeout(() => {
    callAJAX(element.value, cmd, isIpAddress)
      .then((result) => {
        if (result && statusElements.value[elementName]) {
          statusElements.value[elementName].status = result
        }
      })
      .catch(() => {})
  }, doneTypingInterval)
}

async function callAJAX(
  input: string | undefined,
  cmd: PingCmd = PingCmd.Ping,
  isIpAddress: boolean = false
): Promise<DNSStatus | null> {
  if (ajaxRequestInProgress.value[cmd]) {
    controller.value.abort('New request triggered, aborting previous one')
  }
  while (controller.value.signal.aborted) {
    // Wait for the previous request to finish
    await new Promise((resolve) => setTimeout(resolve, 10))
  }
  const siteId = props.sites.find((site) => site.id_hash === props.siteSelectElement.value)?.site_id
  const currentInput = input ? encodeURIComponent(input) : undefined

  if (!currentInput) {
    return null
  }

  ajaxRequestInProgress.value[cmd] = true
  return await axios
    .post('ajax_ping_host.py', null, {
      signal: controller.value.signal,
      params: {
        site_id: siteId ? encodeURIComponent(siteId) : undefined,
        ip_or_dns_name: currentInput,
        cmd: cmd
      }
    })
    .then((response) => {
      if (response.data) {
        return handlePingHostResult(response.data, isIpAddress)
      }
      return null
    })
    .catch(() => {
      controller.value = new AbortController()
      return null
    })
    .finally(() => {
      ajaxRequestInProgress.value[cmd] = false
    })
}

interface DNSStatus {
  tooltip: string
  status: Variants
}

function handlePingHostResult(response: PingHostResponse, isIpAddress: boolean): DNSStatus {
  switch (response.result_code) {
    case 0:
      switch (response.result.status_code) {
        case 0:
          return {
            tooltip: isIpAddress
              ? props.i18n.success_ip_pingable
              : props.i18n.success_host_dns_resolvable,
            status: 'success'
          }
        default:
          return {
            tooltip: isIpAddress
              ? props.i18n.error_ip_not_pingable
              : props.i18n.error_host_not_dns_resolvable,
            status: 'warning'
          }
      }
    case 1:
      return {
        tooltip: response.result,
        status: 'error'
      }
  }
}
</script>

<template>
  <Teleport
    v-for="[elementName, { status, element }] in Object.entries(statusElements)"
    :key="elementName"
    :to="element.parentNode"
    defer
  >
    <span class="mh-ping-host__status-box">
      <CmkAlertBox
        :title="status.tooltip"
        :variant="status.status"
        size="small"
        class="mh-ping-host__status-box-alert"
      >
        {{ status.tooltip }}
      </CmkAlertBox>
    </span>
  </Teleport>
</template>

<style scoped>
.mh-ping-host__status-box {
  display: inline-block;
  position: relative;
  top: 4px;

  .mh-ping-host__status-box-alert {
    margin: 0;
  }
}
</style>
