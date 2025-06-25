<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onMounted, ref, type Ref } from 'vue'
import axios from 'axios'
import StatusBox, { type DNSStatus } from '@/mode-host/ping-host/StatusBox.vue'
import { type I18NPingHost, type ModeHostSite } from 'cmk-shared-typing/typescript/mode_host'

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
  Ping4 = 'ping4',
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
const controller = ref(new AbortController())
const ajaxRequestInProgress = ref(false)

const typingTimer: Ref<ReturnType<typeof setTimeout> | null> = ref(null)
const doneTypingInterval = 250

onMounted(() => {
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
        if (isNoIP.value) {
          statusElements.value = {}
        }
        break
    }
  })
  props.hostnameInputElement.addEventListener('input', () => {
    if (isNoIP.value) {
      statusElements.value = {}
      return
    }
    if (props.ipv4InputButtonElement.checked || props.ipv6InputButtonElement.checked) {
      return
    }
    callPingHostOnElement(props.hostnameInputElement, PingCmd.Ping, false)
  })
  props.ipv4InputElement.addEventListener('input', () => {
    if (isNoIP.value) {
      statusElements.value = {}
      return
    }
    callPingHostOnElement(props.ipv4InputElement, PingCmd.Ping4, true)
  })
  props.ipv6InputElement.addEventListener('input', () => {
    if (isNoIP.value) {
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
  if (typingTimer.value) {
    clearTimeout(typingTimer.value)
  }
  const elementName = element.name
  if (!elementName) {
    return
  }
  if (!element.value) {
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
  typingTimer.value = setTimeout(() => {
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
  if (ajaxRequestInProgress.value) {
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

  ajaxRequestInProgress.value = true
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
      ajaxRequestInProgress.value = false
    })
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
            status: 'ok'
          }
        default:
          return {
            tooltip: isIpAddress
              ? props.i18n.error_ip_not_pingable
              : props.i18n.error_host_not_dns_resolvable,
            status: 'warn'
          }
      }
    case 1:
      return {
        tooltip: response.result,
        status: 'crit'
      }
  }
}
</script>

<template>
  <Teleport
    v-for="[elementName, { status, element }] in Object.entries(statusElements)"
    :key="elementName"
    :to="element.parentNode"
  >
    <StatusBox :status="status" />
  </Teleport>
</template>
