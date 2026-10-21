<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'
import type { ConsolidationFunction } from 'cmk-shared-typing/typescript/consolidation'
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkTabs, { CmkTab, CmkTabContent } from 'cmk-ui-library/components/CmkTabs'
import FormAutocompleter from 'cmk-ui-library/components/FormAutocompleter/FormAutocompleter.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed } from 'vue'

import { appendedAttributeNames } from '../definition'

const { _t } = usei18n()

const {
  consolidation,
  aggregator,
  appendSeriesAttributes,
  templateErrors = []
} = defineProps<{
  consolidation: ConsolidationFunction
  aggregator: Aggregator | undefined
  appendSeriesAttributes: boolean
  templateErrors?: string[]
}>()

const serviceName = defineModel<string>('serviceName', { required: true })
const hostName = defineModel<string | null>('hostName', { required: true })
const hostNameTemplate = defineModel<string | null>('hostNameTemplate', { required: true })

type AssignmentMode = 'manual' | 'automatic'

const assignmentMode = computed<AssignmentMode>(() =>
  hostNameTemplate.value === null ? 'manual' : 'automatic'
)

// Switching discards what was configured for the other mode
function selectAssignmentMode(mode: string | number): void {
  if (mode === assignmentMode.value) {
    return
  }
  hostName.value = null
  hostNameTemplate.value = mode === 'automatic' ? '' : null
}

const appendedAttributes = computed<string>(() => {
  if (!appendSeriesAttributes) {
    return ''
  }
  const names = appendedAttributeNames(consolidation, aggregator)
  return names === null ? _t('+ all attributes') : names.map((name) => `+ ${name}`).join(' ')
})

// Dedicated custom-service host autocompleter: searches configured hosts by
// name and IP, permission-filtered, and returns only existing hosts (no free
// entry) — see cmk/telemetry/gui/custom_services/_autocompleters.py.
const hostAutocompleter: Autocompleter = {
  fetch_method: 'rest_autocomplete',
  data: { ident: 'otel_custom_service_host', params: {} }
}

const hostFieldId = useId()
const serviceNameHelpId = useId()
const assignmentLabelId = useId()
const templateFieldId = useId()
</script>

<template>
  <div class="mode-custom-services-assign-host-step">
    <CmkParagraph>{{ _t('Register this metric as a service on a host.') }}</CmkParagraph>

    <label class="mode-custom-services-assign-host-step__field">
      <span class="mode-custom-services-assign-host-step__label">{{ _t('Service name') }}</span>
      <CmkInput
        v-model="serviceName"
        field-size="large"
        :unit="appendedAttributes"
        :described-by="appendSeriesAttributes ? serviceNameHelpId : undefined"
      />
    </label>
    <CmkParagraph
      v-if="appendSeriesAttributes"
      :id="serviceNameHelpId"
      class="mode-custom-services-assign-host-step__help"
      >{{
        _t(
          'The attribute values of each series are appended to this name, so that every series gets its own service, e.g. "http.server.duration GET - 200". Very long names are shortened and end in a short hash. Use "Group by" to append only the grouped attributes: this keeps the names short and stable, as every new attribute value creates a new service.'
        )
      }}</CmkParagraph
    >

    <div class="mode-custom-services-assign-host-step__field">
      <span :id="assignmentLabelId" class="mode-custom-services-assign-host-step__label">{{
        _t('Assignment')
      }}</span>
      <CmkTabs
        :model-value="assignmentMode"
        :aria-labelledby="assignmentLabelId"
        @update:model-value="selectAssignmentMode"
      >
        <template #tabs>
          <CmkTab id="manual">{{ _t('Manual') }}</CmkTab>
          <CmkTab id="automatic">{{ _t('Automatic') }}</CmkTab>
        </template>
        <template #tab-contents>
          <CmkTabContent id="manual">
            <div class="mode-custom-services-assign-host-step__tab-form">
              <CmkParagraph class="mode-custom-services-assign-host-step__tab-description">{{
                _t('Select one host to add the service to.')
              }}</CmkParagraph>
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
            </div>
          </CmkTabContent>
          <CmkTabContent id="automatic">
            <div class="mode-custom-services-assign-host-step__tab-form">
              <CmkParagraph class="mode-custom-services-assign-host-step__tab-description">{{
                _t(
                  'Derive the host from a host name template, so every matching host gets the service.'
                )
              }}</CmkParagraph>
              <div class="mode-custom-services-assign-host-step__field">
                <CmkLabel
                  variant="subtitle"
                  :for="templateFieldId"
                  :help="
                    _t(
                      'Every combination of attribute values the template references resolves to one host name, e.g. $RESOURCE_ATTR.service.name$. The service is created on the configured hosts the template resolves to when saving.'
                    )
                  "
                  >{{ _t('Host name template') }}</CmkLabel
                >
                <CmkInput
                  :id="templateFieldId"
                  :model-value="hostNameTemplate ?? ''"
                  field-size="fill"
                  :placeholder="_t('e.g. $RESOURCE_ATTR.service.name$')"
                  :external-errors="templateErrors"
                  @update:model-value="(value) => (hostNameTemplate = value ?? '')"
                />
              </div>
            </div>
          </CmkTabContent>
        </template>
      </CmkTabs>
    </div>

    <div v-if="assignmentMode === 'manual'" class="mode-custom-services-assign-host-step__preview">
      <span class="mode-custom-services-assign-host-step__label">
        {{ _t('Services to be created') }} ({{ hostName ? 1 : 0 }})
      </span>
      <div v-if="hostName" class="mode-custom-services-assign-host-step__summary">
        <span
          >{{ _t('Service:') }} <strong>{{ serviceName }}</strong>
          <template v-if="appendedAttributes">{{ appendedAttributes }}</template></span
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
}

.mode-custom-services-assign-host-step__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.mode-custom-services-assign-host-step__tab-form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
}

.mode-custom-services-assign-host-step__tab-description {
  font-size: var(--font-size-small);
}

.mode-custom-services-assign-host-step__label {
  font-weight: bold;
  font-size: var(--font-size-small);
}

.mode-custom-services-assign-host-step__help {
  margin-top: calc(-1 * var(--dimension-3));
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
