<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkLabel from '@/components/CmkLabel.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

import type { EventConsoleConfig } from './ConfigureCollector.vue'

const { _t } = usei18n()

const props = defineProps<{
  encryptionAllowed: boolean
  eventConsoleAllowed: boolean
  showErrors: boolean
}>()

const encryption = defineModel<boolean>('encryption', { required: true })
const eventConsole = defineModel<EventConsoleConfig | null>('eventConsole', { required: true })

const eventConsoleErrors = computed((): string[] => {
  if (!props.showErrors) {
    return []
  }
  if (eventConsole.value !== null && !eventConsole.value.resourceAttribute.trim()) {
    return [
      _t(
        'You must set a resource attribute (e.g., service.name) so the system can determine the host name.'
      )
    ]
  }
  return []
})
</script>

<template>
  <template v-if="encryptionAllowed">
    <CmkLabel>{{ _t('Encryption') }}</CmkLabel>
    <CmkCheckbox v-model="encryption" :label="_t('Encrypt communication with TLS')" />
  </template>

  <template v-if="eventConsoleAllowed">
    <CmkLabel>{{ _t('Event Console') }}</CmkLabel>
    <CmkCheckbox
      :model-value="eventConsole !== null"
      :label="_t('Send log messages to event console')"
      @update:model-value="eventConsole = $event ? { resourceAttribute: '' } : null"
    />
    <template v-if="eventConsole !== null">
      <span />
      <div class="mode-otel-collector-connection-options__sub-field">
        <CmkLabel
          >{{ _t('Resource attribute for host name lookup') }} <CmkLabelRequired
        /></CmkLabel>
        <CmkInput
          v-model="eventConsole.resourceAttribute"
          type="text"
          field-size="MEDIUM"
          placeholder="service.name"
          :external-errors="eventConsoleErrors"
        />
      </div>
    </template>
  </template>
</template>

<style scoped>
.mode-otel-collector-connection-options__sub-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing) var(--dimension-6);
  margin-left: var(--spacing);
  border-left: var(--button-form-border-color) 1px solid;
  padding-left: var(--spacing);
}
</style>
