<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import FormAutocompleter from 'cmk-ui-library/components/FormAutocompleter/FormAutocompleter.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'

const { _t } = usei18n()

const serviceName = defineModel<string>('serviceName', { required: true })
const hostName = defineModel<string | null>('hostName', { required: true })

// Dedicated custom-service host autocompleter: searches configured hosts by
// name and IP, permission-filtered, and returns only existing hosts (no free
// entry) — see cmk/telemetry/gui/custom_services/_autocompleters.py.
const hostAutocompleter: Autocompleter = {
  fetch_method: 'rest_autocomplete',
  data: { ident: 'otel_custom_service_host', params: {} }
}

const hostFieldId = useId()
</script>

<template>
  <div class="mode-custom-services-assign-host-step">
    <CmkParagraph>{{ _t('Register this metric as a service on a host.') }}</CmkParagraph>

    <label class="mode-custom-services-assign-host-step__field">
      <span class="mode-custom-services-assign-host-step__label">{{ _t('Service name') }}</span>
      <CmkInput v-model="serviceName" field-size="large" />
    </label>

    <div class="mode-custom-services-assign-host-step__field">
      <CmkLabel variant="subtitle" :for="hostFieldId">{{ _t('Select host') }}</CmkLabel>
      <FormAutocompleter
        :id="hostFieldId"
        :model-value="hostName"
        :autocompleter="hostAutocompleter"
        :size="0"
        :placeholder="_t('Search hosts by name…')"
        width="wide"
        floating
        @update:model-value="hostName = $event"
      />
    </div>

    <div class="mode-custom-services-assign-host-step__preview">
      <span class="mode-custom-services-assign-host-step__label">
        {{ _t('Services to be created') }} ({{ hostName ? 1 : 0 }})
      </span>
      <div v-if="hostName" class="mode-custom-services-assign-host-step__summary">
        <span
          >{{ _t('Service:') }} <strong>{{ serviceName }}</strong></span
        >
        <span
          >{{ _t('Target host:') }} <strong>{{ hostName }}</strong></span
        >
      </div>
    </div>
  </div>
</template>

<style scoped>
.mode-custom-services-assign-host-step {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  max-width: 620px;
}

.mode-custom-services-assign-host-step__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.mode-custom-services-assign-host-step__label {
  font-weight: bold;
  font-size: var(--font-size-small);
}

.mode-custom-services-assign-host-step__preview {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  padding-top: var(--dimension-3);
  border-top: 1px solid var(--ux-theme-6, rgb(255 255 255 / 10%));
}

.mode-custom-services-assign-host-step__summary {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  font-size: var(--font-size-small);
}
</style>
