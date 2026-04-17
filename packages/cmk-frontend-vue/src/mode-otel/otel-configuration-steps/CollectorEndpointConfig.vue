<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

import type { EndpointConfig } from './otelTypes'
import { validateAddress, validatePort } from './validation.ts'

const { _t } = usei18n()

const props = defineProps<{
  showErrors: boolean
  bothEndpointsEmpty: boolean
  portConflict: boolean
  defaultPort: number
}>()

const endpoint = defineModel<EndpointConfig>('endpoint', { required: true })

const socketAddressOptions = computed(() => [
  { name: 'default_ipv4', title: _t(`Default IPv4 (0.0.0.0:${props.defaultPort})`) },
  { name: 'default_ipv6', title: _t(`Default IPv6 ([::]:${props.defaultPort})`) },
  { name: 'custom', title: _t('Custom') }
])

const errors = computed((): { address: string[]; port: string[] } => {
  if (
    !props.showErrors ||
    endpoint.value.socketAddressType !== 'custom' ||
    (!endpoint.value.address.trim() &&
      endpoint.value.port === undefined &&
      !props.bothEndpointsEmpty)
  ) {
    return { address: [], port: [] }
  }
  const portErrors = validatePort(endpoint.value.port, _t)
  if (props.portConflict && portErrors.length === 0) {
    portErrors.push(_t('Port must differ from the other protocol endpoint.'))
  }
  return {
    address: !endpoint.value.address.trim()
      ? [_t('Enter a valid IP address or host name.')]
      : validateAddress(endpoint.value.address, _t),
    port: portErrors
  }
})
</script>

<template>
  <CmkLabel>{{ _t('Socket address to listen on') }}</CmkLabel>
  <CmkDropdown
    v-model:selected-option="endpoint.socketAddressType"
    :options="{ type: 'fixed', suggestions: socketAddressOptions }"
    :label="_t('Socket address to listen on')"
  />

  <template v-if="endpoint.socketAddressType === 'custom'">
    <span />
    <div class="mode-otel-collector-endpoint-config__sub-field">
      <CmkLabel>{{ _t('IP address or host name') }} <CmkLabelRequired /></CmkLabel>
      <CmkInput
        v-model="endpoint.address"
        type="text"
        field-size="MEDIUM"
        placeholder="0.0.0.0"
        :external-errors="errors.address"
      />
      <CmkLabel>{{ _t('Port') }} <CmkLabelRequired /></CmkLabel>
      <CmkInput
        v-model="endpoint.port"
        type="number"
        :placeholder="defaultPort"
        :external-errors="errors.port"
      />
    </div>
  </template>
</template>

<style scoped>
.mode-otel-collector-endpoint-config__sub-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing) var(--dimension-6);
  margin-left: var(--spacing);
  border-left: var(--button-form-border-color) 1px solid;
  padding-left: var(--spacing);
}
</style>
