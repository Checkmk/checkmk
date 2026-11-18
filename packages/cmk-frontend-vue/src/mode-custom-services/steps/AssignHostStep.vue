<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'
import type { ConsolidationFunction } from 'cmk-shared-typing/typescript/consolidation'
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkHelpText from 'cmk-ui-library/components/CmkHelpText.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkTabs, { CmkTab, CmkTabContent } from 'cmk-ui-library/components/CmkTabs'
import FormAutocompleter from 'cmk-ui-library/components/FormAutocompleter/FormAutocompleter.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref, watch } from 'vue'

import { fetchTemplateAttributes } from '../api'
import {
  type ServicesToCreate,
  type TemplateAttributes,
  appendedAttributesOfGrouping,
  templateMacro
} from '../definition'
import { useOpenTelemetryData } from '../openTelemetryData'
import type { ServicesPreview } from '../servicesPreview'
import type { TemplatePreview } from '../templatePreview'
import OpenTelemetryDataNotice from './OpenTelemetryDataNotice.vue'
import ServicesToBeCreated from './ServicesToBeCreated.vue'
import TemplateHostMatches from './TemplateHostMatches.vue'

const { _t } = usei18n()

const {
  metricName,
  attributeFilter,
  consolidation,
  aggregator,
  appendSeriesAttributes,
  templatePreview,
  servicesPreview,
  templateErrors = []
} = defineProps<{
  metricName: string | null
  attributeFilter: AttributeFilter | undefined
  consolidation: ConsolidationFunction
  aggregator: Aggregator | undefined
  appendSeriesAttributes: boolean
  templatePreview: TemplatePreview
  servicesPreview: ServicesPreview
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

const templateAttributes = ref<TemplateAttributes | null>(null)
const templateAttributesError = ref<string | null>(null)
let templateAttributesRequest = 0

watch(
  () => [assignmentMode.value, metricName, attributeFilter, consolidation, aggregator] as const,
  async ([mode, metric]) => {
    const request = ++templateAttributesRequest
    templateAttributes.value = null
    templateAttributesError.value = null
    if (mode !== 'automatic' || metric === null) {
      return
    }
    try {
      const attributes = await fetchTemplateAttributes({
        metric_name: metric,
        ...(attributeFilter === undefined ? {} : { attribute_filter: attributeFilter }),
        consolidation,
        ...(aggregator === undefined ? {} : { aggregator })
      })
      if (request === templateAttributesRequest) {
        templateAttributes.value = attributes
      }
    } catch (error) {
      if (request === templateAttributesRequest) {
        templateAttributesError.value =
          error instanceof Error ? error.message : _t('The attributes could not be loaded.')
      }
    }
  },
  { immediate: true }
)

function insertMacro(macro: string): void {
  hostNameTemplate.value = `${hostNameTemplate.value ?? ''}${macro}`
}

type AppendedAttributes = ServicesToCreate['appended_attributes']

// What the names append is known once the services resolve. Kept while the next lookup runs, so
// that the indicator does not flicker while typing.
const appended = ref<AppendedAttributes | null>(null)
watch(
  () => servicesPreview,
  (preview) => {
    if (preview.status === 'resolved') {
      appended.value = preview.services.appended_attributes
    } else if (preview.status !== 'loading') {
      appended.value = null
    }
  },
  { immediate: true }
)

// Until the services resolve, guessed from the grouping alone: the host name template, the filter
// and the service name may leave out more.
const guessed = computed<AppendedAttributes>(() => {
  if (!appendSeriesAttributes) {
    return { all_attributes: false, attributes: [] }
  }
  const attributes = appendedAttributesOfGrouping(consolidation, aggregator)
  return attributes === null
    ? { all_attributes: true, attributes: [] }
    : { all_attributes: false, attributes }
})

const shown = computed<AppendedAttributes>(() => appended.value ?? guessed.value)

const appendedAttributes = computed<string>(() => {
  const { all_attributes: allAttributes, attributes } = shown.value
  if (allAttributes) {
    return _t('+ all attributes')
  }
  if (attributes.length === 1) {
    return `+ ${attributes[0]!.key}`
  }
  return attributes.length > 1 ? _t('+ grouped attributes') : ''
})

// By its key, as the indicator shows it. Only two appended attributes of different kinds sharing a
// key are told apart by their macros.
function attributeLabel(
  attribute: AppendedAttributes['attributes'][number],
  attributes: AppendedAttributes['attributes']
): string {
  const shared = attributes.filter((other) => other.key === attribute.key).length > 1
  return shared ? templateMacro(attribute) : attribute.key
}

const appendedAttributesHelp = computed<TranslatedString>(() => {
  const { all_attributes: allAttributes, attributes } = shown.value
  if (allAttributes) {
    return _t(
      'The attribute values of each series are appended to this name so that every series gets its own service, for example "http.server.duration GET - 200". Values that are part of the host name, fixed by the filter or already shown in the name are left out. Names that are too long are shortened and end in a short hash. Each new attribute value creates a new service, for example a new pod after a deployment. To keep names short and services stable, group the series by the attributes you need. Only their values are then appended.'
    )
  }
  if (attributes.length === 1) {
    return _t(
      'The value of the grouped attribute %{attribute} is appended to this name so that every group gets its own service, for example "http.server.duration /cart". Names that are too long are shortened and end in a short hash.',
      { attribute: attributeLabel(attributes[0]!, attributes) }
    )
  }
  if (attributes.length > 1) {
    return _t(
      'The values of the grouped attributes (%{attributes}) are appended to this name so that every group gets its own service, for example "http.server.duration GET - 200". Names that are too long are shortened and end in a short hash.',
      {
        attributes: attributes.map((attribute) => attributeLabel(attribute, attributes)).join(', ')
      }
    )
  }
  return _t(
    'Nothing is appended to this name, so the service is named as entered, with its macros filled in.'
  )
})

// Dedicated custom-service host autocompleter: searches configured hosts by
// name and IP, permission-filtered, and returns only existing hosts (no free
// entry) — see cmk/telemetry/gui/custom_services/_autocompleters.py.
const hostAutocompleter: Autocompleter = {
  fetch_method: 'rest_autocomplete',
  data: { ident: 'otel_custom_service_host', params: {} }
}

const openTelemetryData = useOpenTelemetryData(() => {
  if (assignmentMode.value === 'manual') {
    return hostName.value ? [hostName.value] : []
  }
  return templatePreview.status === 'resolved' ? templatePreview.resolution.matching_hosts : []
})

const serviceNameMacroHelp = untranslated(
  [
    _t(
      'Combine free text with macros to name each service after the data it monitors: every macro is replaced by the matching value of each series, such as the metric name or an OpenTelemetry attribute, so different series can get their own services.'
    ),
    '',
    _t('Available service name macros:'),
    [
      '$METRIC_NAME$',
      '$SERIES_ID$',
      '$RESOURCE_ATTR.&lt;key&gt;$',
      '$SCOPE_ATTR.&lt;key&gt;$',
      '$DATA_POINT_ATTR.&lt;key&gt;$'
    ]
      .map((macro) => `<tt>${macro}</tt>`)
      .join(', ')
  ].join('<br>')
)

const serviceNameFieldId = useId()
const hostFieldId = useId()
const assignmentLabelId = useId()
const templateFieldId = useId()
</script>

<template>
  <div class="mode-custom-services-assign-host-step">
    <CmkParagraph>{{ _t('Monitor this metric as a service on a host.') }}</CmkParagraph>

    <div class="mode-custom-services-assign-host-step__field">
      <CmkLabel :for="serviceNameFieldId" :help="serviceNameMacroHelp"
        ><span class="mode-custom-services-assign-host-step__label">{{ _t('Service name') }}</span
        ><CmkLabelRequired space="before"
      /></CmkLabel>
      <div class="mode-custom-services-assign-host-step__service-name">
        <CmkInput
          :id="serviceNameFieldId"
          v-model="serviceName"
          field-size="large"
          :unit="appendedAttributes"
        />
        <CmkHelpText
          :aria-label="_t('About the appended attributes')"
          :help="appendedAttributesHelp"
        />
      </div>
    </div>

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
              <CmkParagraph>{{ _t('Select one host to add the service(s) to.') }}</CmkParagraph>
              <div class="mode-custom-services-assign-host-step__field">
                <CmkLabel :for="hostFieldId"
                  ><span class="mode-custom-services-assign-host-step__label">{{
                    _t('Select host')
                  }}</span
                  ><CmkLabelRequired space="before"
                /></CmkLabel>
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
              <CmkParagraph>{{
                _t(
                  'Derive the host from a host name template, so every matching host gets the service.'
                )
              }}</CmkParagraph>
              <div class="mode-custom-services-assign-host-step__field">
                <CmkLabel
                  :for="templateFieldId"
                  :help="
                    _t(
                      'Click an attribute to insert its placeholder. Every combination of attribute values the template references resolves to one host name. The service is created on the configured hosts the template resolves to when saving.'
                    )
                  "
                  ><span class="mode-custom-services-assign-host-step__label">{{
                    _t('Host name template')
                  }}</span
                  ><CmkLabelRequired space="before"
                /></CmkLabel>
                <CmkInput
                  :id="templateFieldId"
                  :model-value="hostNameTemplate ?? ''"
                  field-size="fill"
                  :placeholder="_t('e.g. $RESOURCE_ATTR.service.name$')"
                  :external-errors="templateErrors"
                  @update:model-value="(value) => (hostNameTemplate = value ?? '')"
                />
              </div>
              <div class="mode-custom-services-assign-host-step__tab-notes">
                <CmkParagraph v-if="templateAttributesError">{{
                  templateAttributesError
                }}</CmkParagraph>
                <CmkParagraph v-else-if="templateAttributes?.availability === 'series_merged'">{{
                  _t(
                    'The metric step combines all series into one, so no attribute can tell hosts apart. Group the series by the attributes the template should use.'
                  )
                }}</CmkParagraph>
                <CmkParagraph v-else-if="templateAttributes?.availability === 'no_series'">{{
                  _t('No series of this metric reported any attributes within the last hour.')
                }}</CmkParagraph>
                <div
                  v-else-if="templateAttributes"
                  class="mode-custom-services-assign-host-step__attributes"
                >
                  <CmkButton
                    v-for="attribute in templateAttributes.attributes"
                    :key="`${attribute.kind}:${attribute.key}`"
                    variant="optional"
                    size="small"
                    :title="templateMacro(attribute)"
                    @click="insertMacro(templateMacro(attribute))"
                    >+ {{ attribute.key }}</CmkButton
                  >
                  <CmkParagraph v-if="templateAttributes.truncated">{{
                    _t('Only the first attributes of each kind are listed.')
                  }}</CmkParagraph>
                </div>
              </div>
            </div>
          </CmkTabContent>
        </template>
      </CmkTabs>
    </div>

    <div class="mode-custom-services-assign-host-step__preview">
      <ServicesToBeCreated :preview="servicesPreview" />
      <OpenTelemetryDataNotice
        v-if="assignmentMode === 'manual' && hostName"
        :data="openTelemetryData"
      />
      <TemplateHostMatches
        v-else-if="assignmentMode === 'automatic'"
        :preview="templatePreview"
        :opentelemetry-data="openTelemetryData"
      />
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
  gap: var(--dimension-4);
}

.mode-custom-services-assign-host-step__tab-form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
}

.mode-custom-services-assign-host-step__tab-notes {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.mode-custom-services-assign-host-step__label {
  font-weight: bold;
}

.mode-custom-services-assign-host-step__service-name {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

.mode-custom-services-assign-host-step__attributes {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-3);
}

.mode-custom-services-assign-host-step__preview {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  padding-top: var(--dimension-3);
  border-top: 1px solid var(--ux-theme-6, rgb(255 255 255 / 10%));
}
</style>
