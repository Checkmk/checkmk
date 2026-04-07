<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkLabel from '@/components/CmkLabel.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

import type { EndpointConfig } from './ConfigureCollector.vue'
import { validateAddress, validatePort } from './validation.ts'

const { _t } = usei18n()

const props = defineProps<{
  showErrors: boolean
  bothEndpointsEmpty: boolean
  addressPlaceholder: string
  portPlaceholder: string
}>()

const endpoint = defineModel<EndpointConfig>('endpoint', { required: true })

const errors = computed((): { address: string[]; port: string[] } => {
  if (!props.showErrors) {
    return { address: [], port: [] }
  }
  const hasInput = !!endpoint.value.address.trim() || endpoint.value.port !== undefined
  if (!hasInput && !props.bothEndpointsEmpty) {
    return { address: [], port: [] }
  }
  return {
    address: !endpoint.value.address.trim()
      ? props.bothEndpointsEmpty
        ? [_t('Enter a valid IP address or host name.')]
        : []
      : validateAddress(endpoint.value.address, _t),
    port: hasInput ? validatePort(endpoint.value.port, _t) : []
  }
})
</script>

<template>
  <CmkLabel>{{ _t('IP address or host name') }} <CmkLabelRequired /></CmkLabel>
  <CmkInput
    v-model="endpoint.address"
    type="text"
    field-size="MEDIUM"
    :placeholder="addressPlaceholder"
    :external-errors="errors.address"
  />
  <CmkLabel>{{ _t('Port') }} <CmkLabelRequired /></CmkLabel>
  <CmkInput
    v-model="endpoint.port"
    type="number"
    :placeholder="portPlaceholder"
    :external-errors="errors.port"
  />
</template>
