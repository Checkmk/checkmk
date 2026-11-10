<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import CmkHelpText from 'cmk-ui-library/components/CmkHelpText.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import type { CmkWizardStepProps } from 'cmk-ui-library/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { FormEdit, type ValidationMessages } from '@/form'

import CustomServiceSelect from '@/mode-alerts/CustomServiceSelect.vue'
import { formSpecErrors } from '@/mode-alerts/conditions-validation'
import {
  type FoundService,
  type ServiceSearchResult,
  type UnitSummary,
  patternErrorOf,
  searchServices
} from '@/mode-alerts/service-client'
import {
  type AlertModel,
  type FolderPaths,
  alertConditions,
  servicePattern
} from '@/mode-alerts/types'

const SEARCH_DEBOUNCE_MS = 200
const PREVIEW_LIMIT = 5

const { _t, _tn } = usei18n()

const {
  conditionsSpec,
  folderPaths,
  isFirst = false,
  prefilled = false,
  matchMaySelectOthers = false
} = defineProps<
  CmkWizardStepProps & {
    conditionsSpec: FormSpec
    folderPaths: FolderPaths
    isFirst?: boolean
    prefilled?: boolean
    // The service name, taken over from a custom service, may select other services as well
    matchMaySelectOthers?: boolean
  }
>()

const model = defineModel<AlertModel>({ required: true })

const patternFieldId = useId()

const matchTypeOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'exact', title: _t('Exact match') },
    { name: 'regex', title: _t('Regular expression') }
  ]
}))

const selectedMatchType = computed<string | null>({
  get: () => model.value.matchType,
  set: (value) => {
    model.value.matchType = value === 'regex' ? 'regex' : 'exact'
  }
})

// CmkDropdown models an empty selection as null, the alert model as an empty string.
const selectedServiceName = computed({
  get: () => (model.value.servicePattern === '' ? null : model.value.servicePattern),
  set: (value) => {
    model.value.servicePattern = value ?? ''
  }
})

const conditions = computed(() => alertConditions(model.value, folderPaths))

const matches = ref<ServiceSearchResult | null>(null)
const searching = ref(false)
const searchError = ref<string | null>(null)
// Why the server refused the service pattern, shown at the field.
const refusedPattern = ref<string | null>(null)
const displayErrors = ref(false)
const conditionsValidation = ref<ValidationMessages>([])
const showAllMatches = ref(false)

// Discards the result of a search whose pattern has since been replaced, so two searches
// resolving out of order cannot leave the older one on screen.
let searchToken = 0
let debounceTimer: ReturnType<typeof setTimeout> | undefined

function getPatternErrors(): string[] {
  if (servicePattern(model.value) === '') {
    return [_t('A service name is required')]
  }
  return refusedPattern.value === null ? [] : [refusedPattern.value]
}

const patternErrors = computed(() =>
  displayErrors.value || refusedPattern.value !== null ? getPatternErrors() : []
)

const noMatches = computed(() => matches.value !== null && matches.value.total === 0)

const visibleMatches = computed(() =>
  showAllMatches.value
    ? (matches.value?.services ?? [])
    : (matches.value?.services ?? []).slice(0, PREVIEW_LIMIT)
)

// The services found but not listed, beyond those on hosts the user may not see.
const unlisted = computed(() =>
  matches.value === null
    ? 0
    : matches.value.total - matches.value.hidden - matches.value.services.length
)

async function search(): Promise<void> {
  if (servicePattern(model.value) === '') {
    return
  }
  const token = ++searchToken
  searching.value = true
  searchError.value = null
  try {
    const result = await searchServices(
      model.value.matchType,
      servicePattern(model.value),
      conditions.value
    )
    if (token !== searchToken) {
      return
    }
    matches.value = result
    showAllMatches.value = false
  } catch (error) {
    if (token !== searchToken) {
      return
    }
    matches.value = null
    refusedPattern.value = patternErrorOf(error)
    if (refusedPattern.value === null) {
      searchError.value =
        error instanceof CmkApiError && (error.statusCode < 500 || error.statusCode === 503)
          ? error.message
          : _t('Failed to search for custom services.')
    }
  } finally {
    if (token === searchToken) {
      searching.value = false
    }
  }
}

function cancelPendingSearch(): void {
  if (debounceTimer !== undefined) {
    clearTimeout(debounceTimer)
    debounceTimer = undefined
  }
}

// A result list left over from an earlier pattern would be misleading. The token is
// invalidated here, not in `search()`, which a cleared pattern never reaches.
watch(
  [
    () => model.value.servicePattern,
    () => model.value.matchType,
    () => JSON.stringify(conditions.value)
  ],
  () => {
    searchToken++
    matches.value = null
    searching.value = false
    searchError.value = null
    refusedPattern.value = null
    cancelPendingSearch()
    debounceTimer = setTimeout(() => void search(), SEARCH_DEBOUNCE_MS)
  }
)

// The watch above only searches on a change, so a stored alert would show no matches until
// the user edits something.
onMounted(() => {
  if (prefilled) {
    void search()
  }
})

onBeforeUnmount(cancelPendingSearch)

async function validate(): Promise<boolean> {
  displayErrors.value = true
  cancelPendingSearch()
  conditionsValidation.value = formSpecErrors(conditionsSpec, model.value.conditions)
  if (getPatternErrors().length > 0 || conditionsValidation.value.length > 0) {
    return false
  }
  if (matches.value === null) {
    await search()
  }
  if (getPatternErrors().length > 0 || searchError.value !== null || matches.value === null) {
    return false
  }
  if (matches.value.total === 0) {
    return false
  }
  return unitsError.value === null
}

function unitLabel(unit: string | null | undefined): string {
  if (unit === null || unit === undefined) {
    return _t('unit unknown')
  }
  return unit === '' ? _t('no unit') : unit
}

function rowUnit(service: FoundService): string {
  if (service.unit === null || service.unit === undefined) {
    return _t('unit unknown (no recent data)')
  }
  return unitLabel(service.unit)
}

function unitWithExample(entry: UnitSummary): string {
  const example = entry.example
  if (example === null || example === undefined) {
    return _t('%{unit} (on hosts you cannot see)', { unit: unitLabel(entry.unit) })
  }
  return _t('%{unit} (%{service} on %{host})', {
    unit: unitLabel(entry.unit),
    service: example.service_name,
    host: example.host_name
  })
}

// The units cover every service found, not only the listed ones, as the alert applies to all.
const unitsError = computed(() => {
  const units = matches.value?.units ?? []
  if (units.length <= 1) {
    return null
  }
  return _t(
    'The selected services have different units: %{units}. You must select services with the same units to set levels on them.',
    { units: units.map(unitWithExample).join(', ') }
  )
})
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h3">{{ _t('Select services') }}</CmkHeading>
    </template>

    <template #content>
      <div class="mode-alerts-services-step">
        <CmkParagraph>
          {{ _t('Select the custom services the alert applies to by their service name.') }}
        </CmkParagraph>

        <div class="mode-alerts-services-step__field">
          <CmkLabel :for="patternFieldId">
            {{ _t('Service name') }}
            <CmkLabelRequired />
            <CmkHelpText
              :aria-label="_t('How are service names matched?')"
              :help="
                _t(
                  'Exact matching needs the complete service name. A regular expression matches from the start of the service name, so begin it with .* to match anywhere in it.'
                )
              "
            />
          </CmkLabel>
          <div class="mode-alerts-services-step__service-row">
            <CmkDropdown
              v-model="selectedMatchType"
              :options="matchTypeOptions"
              :label="_t('Match service name by')"
            />
            <CustomServiceSelect
              :id="patternFieldId"
              v-model="selectedServiceName"
              :match-type="model.matchType"
              :conditions="conditions"
              :has-error="patternErrors.length > 0"
            />
          </div>
          <CmkAlert
            v-if="matchMaySelectOthers"
            variant="warning"
            size="small"
            :text="
              _t(
                'This service name may also match other custom services on these hosts. Review it before you continue.'
              )
            "
          />
          <CmkAlert
            v-for="error in patternErrors"
            :key="error"
            variant="error"
            size="small"
            :text="untranslated(error)"
          />
        </div>

        <div class="mode-alerts-services-step__field">
          <CmkHeading type="h4">{{ _t('Conditions') }}</CmkHeading>
          <FormEdit
            v-model:data="model.conditions"
            :spec="conditionsSpec"
            :backend-validation="conditionsValidation"
          />
        </div>

        <CmkAlert
          v-if="searchError"
          variant="error"
          size="small"
          :text="untranslated(searchError)"
        />

        <CmkLoading v-if="searching" />

        <CmkAlert
          v-else-if="noMatches"
          :variant="displayErrors ? 'error' : 'warning'"
          size="small"
          :text="
            _t(
              'No matching services. A custom service is found once it is discovered or its series reported in the last 10 minutes.'
            )
          "
        />

        <div v-else-if="matches" class="mode-alerts-services-step__results">
          <div class="mode-alerts-services-step__results-header">
            <CmkLabel variant="subtitle">
              {{ _t('Matching services') }} ({{ matches.total }})
            </CmkLabel>
            <CmkButton
              v-if="matches.services.length > PREVIEW_LIMIT"
              variant="text"
              size="small"
              @click="showAllMatches = !showAllMatches"
            >
              {{ showAllMatches ? _t('show preview') : _t('show all') }}
            </CmkButton>
          </div>
          <CmkScrollContainer max-height="240px">
            <ul class="mode-alerts-services-step__list">
              <li
                v-for="service in visibleMatches"
                :key="`${service.host_name}:${service.service_name}`"
              >
                <span class="mode-alerts-services-step__name">{{ service.service_name }}</span>
                <CmkChip v-if="!service.discovered" as-div size="small" color="warning">
                  {{ _t('not yet discovered') }}
                </CmkChip>
                <span class="mode-alerts-services-step__unit">{{ rowUnit(service) }}</span>
                <span class="mode-alerts-services-step__host">{{ service.host_name }}</span>
              </li>
            </ul>
          </CmkScrollContainer>
          <CmkParagraph v-if="unlisted > 0">
            {{
              _tn(
                '%{count} more service is not listed. Refine the service name to see it.',
                '%{count} more services are not listed. Refine the service name to see them.',
                unlisted,
                { count: unlisted }
              )
            }}
          </CmkParagraph>
          <CmkParagraph v-if="matches.hidden > 0">
            {{
              _tn(
                '%{count} more service is on a host you cannot see.',
                '%{count} more services are on hosts you cannot see.',
                matches.hidden,
                { count: matches.hidden }
              )
            }}
          </CmkParagraph>
          <CmkAlert
            v-if="matches.undiscovered > 0"
            variant="warning"
            size="small"
            :text="
              _tn(
                '%{count} of these services is not discovered yet. The alert applies to it only after a service discovery on %{hosts}.',
                '%{count} of these services are not discovered yet. The alert applies to them only after a service discovery on %{hosts}.',
                matches.undiscovered,
                { count: matches.undiscovered, hosts: matches.undiscovered_hosts.join(', ') }
              )
            "
          />
          <CmkAlert
            v-if="matches.incomplete_configurations.length > 0"
            variant="warning"
            size="small"
            :text="
              _tn(
                'The custom service %{names} has more series than can be checked here. The alert also applies to its services that are not listed, but their units were not checked.',
                'The custom services %{names} have more series than can be checked here. The alert also applies to their services that are not listed, but their units were not checked.',
                matches.incomplete_configurations.length,
                { names: matches.incomplete_configurations.join(', ') }
              )
            "
          />
          <CmkAlert
            v-if="matches.unreachable_sites.length > 0"
            variant="warning"
            size="small"
            :text="
              _tn(
                'The site %{sites} did not answer, so its services are missing.',
                'The sites %{sites} did not answer, so their services are missing.',
                matches.unreachable_sites.length,
                { sites: matches.unreachable_sites.join(', ') }
              )
            "
          />
        </div>

        <CmkAlert
          v-if="unitsError"
          :variant="displayErrors ? 'error' : 'warning'"
          :text="untranslated(unitsError)"
        />
      </div>
    </template>

    <template #actions>
      <CmkWizardButton type="next" :validation-cb="validate" />
      <CmkWizardButton v-if="!isFirst" type="previous" />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
.mode-alerts-services-step {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  max-width: 620px;
}

.mode-alerts-services-step__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.mode-alerts-services-step__service-row {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.mode-alerts-services-step__service-row > :last-child {
  flex: 1;
  min-width: 0;
}

.mode-alerts-services-step__results {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  padding-top: var(--dimension-3);
  border-top: 1px solid var(--ux-theme-6);
}

.mode-alerts-services-step__results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-4);
}

.mode-alerts-services-step__list {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: var(--font-size-small);
}

.mode-alerts-services-step__list li {
  display: flex;
  justify-content: space-between;
  gap: var(--dimension-4);
  padding: var(--dimension-2) 0;
}

.mode-alerts-services-step__name {
  flex: 1;
}

.mode-alerts-services-step__unit,
.mode-alerts-services-step__host {
  color: var(--font-color-dimmed);
  white-space: nowrap;
}
</style>
