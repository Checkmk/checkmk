<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import type { CmkWizardStepProps } from 'cmk-ui-library/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import CustomServiceSelect from '@/mode-alerts/CustomServiceSelect.vue'
import {
  MAX_MATCHES,
  type ServiceMatches,
  searchCustomServices
} from '@/mode-alerts/service-client'
import { type AlertModel, alertName, hasUnparsableRegex, servicePattern } from '@/mode-alerts/types'

const SEARCH_DEBOUNCE_MS = 200
const PREVIEW_LIMIT = 5

const { _t } = usei18n()

defineProps<CmkWizardStepProps>()

const model = defineModel<AlertModel>({ required: true })

const nameFieldId = useId()
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

const matches = ref<ServiceMatches | null>(null)
const searching = ref(false)
const searchError = ref<string | null>(null)
const displayErrors = ref(false)
const showAllMatches = ref(false)

// Discards the result of a search whose pattern has since been replaced, so two searches
// resolving out of order cannot leave the older one on screen.
let searchToken = 0
let debounceTimer: ReturnType<typeof setTimeout> | undefined

function getNameErrors(): string[] {
  return alertName(model.value) === '' ? [_t('An alert name is required')] : []
}

function getPatternErrors(): string[] {
  if (servicePattern(model.value) === '') {
    return [_t('A service name is required')]
  }
  if (hasUnparsableRegex(model.value)) {
    return [_t('This is not a valid regular expression')]
  }
  return []
}

const nameErrors = computed(() => (displayErrors.value ? getNameErrors() : []))
const patternErrors = computed(() => (displayErrors.value ? getPatternErrors() : []))

const noMatches = computed(() => matches.value !== null && matches.value.services.length === 0)

// An empty result is far more often a name that does not match than a service that was
// never discovered, so lead with the former.
const noMatchHint = computed(() =>
  model.value.matchType === 'exact'
    ? _t(
        'Exact matching needs the complete service name. Switch to a regular expression to match part of it.'
      )
    : _t('Only already discovered custom services can be matched.')
)

const visibleMatches = computed(() =>
  showAllMatches.value
    ? (matches.value?.services ?? [])
    : (matches.value?.services ?? []).slice(0, PREVIEW_LIMIT)
)

async function search(): Promise<void> {
  if (getPatternErrors().length > 0) {
    return
  }
  const token = ++searchToken
  searching.value = true
  searchError.value = null
  try {
    const result = await searchCustomServices(model.value.matchType, servicePattern(model.value))
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
    searchError.value =
      error instanceof CmkApiError && error.statusCode < 500
        ? error.message
        : _t('Failed to search for custom services.')
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
// invalidated here, not in `search()`, which a cleared or unparsable pattern never reaches.
watch([() => model.value.servicePattern, () => model.value.matchType], () => {
  searchToken++
  matches.value = null
  searching.value = false
  searchError.value = null
  cancelPendingSearch()
  debounceTimer = setTimeout(() => void search(), SEARCH_DEBOUNCE_MS)
})

onBeforeUnmount(cancelPendingSearch)

async function validate(): Promise<boolean> {
  displayErrors.value = true
  cancelPendingSearch()
  if (getNameErrors().length > 0 || getPatternErrors().length > 0) {
    return false
  }
  if (matches.value === null) {
    await search()
  }
  return searchError.value === null && (matches.value?.services.length ?? 0) > 0
}
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h3">{{ _t('Name the alert and select services') }}</CmkHeading>
    </template>

    <template #content>
      <div class="mode-alerts-name-and-services-step">
        <CmkParagraph>
          {{
            _t(
              'Name the alert, then select the custom services it applies to by their service name.'
            )
          }}
        </CmkParagraph>

        <div class="mode-alerts-name-and-services-step__field">
          <CmkLabel :for="nameFieldId">
            {{ _t('Alert name') }}
            <CmkLabelRequired />
          </CmkLabel>
          <CmkInput
            :id="nameFieldId"
            v-model="model.name"
            type="text"
            field-size="large"
            :external-errors="nameErrors"
          />
        </div>

        <div class="mode-alerts-name-and-services-step__field">
          <CmkLabel :for="patternFieldId">
            {{ _t('Service name') }}
            <CmkLabelRequired />
          </CmkLabel>
          <div class="mode-alerts-name-and-services-step__service-row">
            <CmkDropdown
              v-model="selectedMatchType"
              :options="matchTypeOptions"
              :label="_t('Match service name by')"
            />
            <CustomServiceSelect
              :id="patternFieldId"
              v-model="selectedServiceName"
              :match-type="model.matchType"
              :has-error="patternErrors.length > 0"
            />
          </div>
          <CmkAlertBox v-for="error in patternErrors" :key="error" variant="error" size="small">
            {{ error }}
          </CmkAlertBox>
        </div>

        <CmkAlertBox v-if="searchError" variant="error" size="small">
          {{ searchError }}
        </CmkAlertBox>

        <CmkLoading v-if="searching" />

        <CmkAlertBox
          v-else-if="noMatches"
          :variant="displayErrors ? 'error' : 'warning'"
          size="small"
        >
          {{ _t('No custom service matches this name.') }} {{ noMatchHint }}
        </CmkAlertBox>

        <div v-else-if="matches" class="mode-alerts-name-and-services-step__results">
          <div class="mode-alerts-name-and-services-step__results-header">
            <CmkLabel variant="subtitle">
              {{ _t('Matching services') }} ({{ matches.services.length
              }}{{ matches.truncated ? '+' : '' }})
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
          <CmkAlertBox v-if="matches.truncated" variant="warning" size="small">
            {{
              _t(
                'Only the first %{count} matches are shown. Refine the service name to narrow them down.',
                { count: MAX_MATCHES }
              )
            }}
          </CmkAlertBox>
          <CmkScrollContainer max-height="240px">
            <ul class="mode-alerts-name-and-services-step__list">
              <li
                v-for="service in visibleMatches"
                :key="`${service.hostName}:${service.serviceName}`"
              >
                <span>{{ service.serviceName }}</span>
                <span class="mode-alerts-name-and-services-step__host">{{ service.hostName }}</span>
              </li>
            </ul>
          </CmkScrollContainer>
        </div>
      </div>
    </template>

    <template #actions>
      <CmkWizardButton type="next" :validation-cb="validate" />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
.mode-alerts-name-and-services-step {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  max-width: 620px;
}

.mode-alerts-name-and-services-step__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.mode-alerts-name-and-services-step__service-row {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.mode-alerts-name-and-services-step__service-row > :last-child {
  flex: 1;
  min-width: 0;
}

.mode-alerts-name-and-services-step__results {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  padding-top: var(--dimension-3);
  border-top: 1px solid var(--ux-theme-6);
}

.mode-alerts-name-and-services-step__results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-4);
}

.mode-alerts-name-and-services-step__list {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: var(--font-size-small);
}

.mode-alerts-name-and-services-step__list li {
  display: flex;
  justify-content: space-between;
  gap: var(--dimension-4);
  padding: var(--dimension-2) 0;
}

.mode-alerts-name-and-services-step__host {
  color: var(--font-color-dimmed);
}
</style>
