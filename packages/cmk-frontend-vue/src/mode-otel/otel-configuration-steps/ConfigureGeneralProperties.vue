<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script lang="ts">
export type RawSite = { id: string; title: string; extensions?: { logged_in?: boolean } }

// Module-level cache so re-entering the step does not trigger a second network call.
let cachedSites: RawSite[] | null = null

/** Exposed for testing only — resets the module-level site cache. */
export function _resetSiteCache(): void {
  cachedSites = null
}
</script>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchRestAPI } from '@/lib/cmkFetch.ts'
import usei18n, { untranslated } from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import type { Suggestion } from '@/components/CmkSuggestions'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

type OTelConfigEntry = {
  extensions?: { site?: string[] }
}

const API_ROOT = 'api/v1'

const { _t } = usei18n()

const props = defineProps<{
  configNamePlaceholder: string
  configListEndpoint: string
  alreadyConfiguredError: string
}>()

const configName = defineModel<string>('configName', { required: true })
const siteId = defineModel<string | null>('siteId', { required: true })

const siteOptions = ref<Suggestion[]>([])
const loadError = ref<string | null>(null)
const isLoading = ref(false)

function applySites(rawSites: RawSite[]) {
  siteOptions.value = rawSites.map((s) => ({
    name: s.id,
    title: untranslated(`${s.id} - ${s.title}`)
  }))
  // Pre-select the local site (no `logged_in` key in extensions) or first entry.
  // Only set when siteId has not been set yet so navigating back preserves the value.
  if (siteId.value === null) {
    const localSite = rawSites.find((s) => !('logged_in' in (s.extensions ?? {})))
    siteId.value = localSite?.id ?? rawSites[0]?.id ?? null
  }
}

onMounted(async () => {
  if (cachedSites !== null) {
    applySites(cachedSites)
    return
  }

  isLoading.value = true
  try {
    const response = await fetchRestAPI(
      `${API_ROOT}/domain-types/site_connection/collections/all`,
      'GET'
    )
    await response.raiseForStatus()
    const data = await response.json()
    cachedSites = data.value as RawSite[]
    applySites(cachedSites)
  } catch {
    loadError.value = _t('Failed to load sites. Please try again.')
  } finally {
    isLoading.value = false
  }
})

const displayErrors = ref(false)

const NAME_PATTERN = /^[a-zA-Z_][a-zA-Z0-9_-]*$/

const configNameErrors = computed<string[]>(() => {
  if (!displayErrors.value) {
    return []
  }
  if (!configName.value.trim()) {
    return [_t('Configuration name is required but not specified.')]
  }
  if (!NAME_PATTERN.test(configName.value)) {
    return [
      _t(
        'The name must only consist of letters, digits, dash and underscore and it must start with a letter or underscore.'
      )
    ]
  }
  return []
})

const siteErrors = ref<string[]>([])

function validateSiteRequired(): string[] {
  if (!siteId.value) {
    return [_t('Site is required but not specified.')]
  }
  return []
}

async function checkSiteAlreadyConfigured(): Promise<string[]> {
  if (!siteId.value) {
    return []
  }

  try {
    const response = await fetchRestAPI(props.configListEndpoint, 'GET')
    await response.raiseForStatus()
    const data = await response.json()

    const hasExistingConfig = data.value.some((config: OTelConfigEntry) =>
      config.extensions?.site?.includes(siteId.value!)
    )

    if (hasExistingConfig) {
      return [props.alreadyConfiguredError]
    }
  } catch {
    return [_t('Failed to validate site configuration. Please try again.')]
  }

  return []
}

async function validate(): Promise<boolean> {
  if (isLoading.value) {
    return false
  }
  displayErrors.value = true

  const requiredErrors = validateSiteRequired()
  if (configNameErrors.value.length > 0 || requiredErrors.length > 0) {
    siteErrors.value = requiredErrors
    return false
  }

  const configErrors = await checkSiteAlreadyConfigured()
  siteErrors.value = [...requiredErrors, ...configErrors]

  return configNameErrors.value.length === 0 && siteErrors.value.length === 0
}

defineExpose({ validate })
</script>

<template>
  <CmkInlineValidation v-if="loadError" :validation="[loadError]" />

  <div class="mode-otel-configure-general-properties__form">
    <!-- Configuration name row -->
    <CmkLabel>{{ _t('Configuration name') }} <CmkLabelRequired /></CmkLabel>
    <CmkInput
      v-model="configName"
      type="text"
      field-size="FILL"
      :placeholder="props.configNamePlaceholder"
      :external-errors="configNameErrors"
    />

    <!-- Site selection row -->
    <CmkLabel>{{ _t('Site selection') }} <CmkLabelRequired /></CmkLabel>
    <div class="mode-otel-configure-general-properties__field-with-error">
      <CmkDropdown
        v-model:selected-option="siteId"
        :options="{ type: 'fixed', suggestions: siteOptions }"
        :input-hint="isLoading ? _t('Loading...') : _t('Select site')"
        :label="_t('Site selection')"
        width="fill"
        :disabled="isLoading"
        :form-validation="siteErrors.length > 0"
      />
      <CmkInlineValidation v-if="siteErrors.length" :validation="siteErrors" />
    </div>
  </div>
</template>

<style scoped>
.mode-otel-configure-general-properties__form {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--spacing) var(--dimension-6);
  align-items: start;
}

.mode-otel-configure-general-properties__field-with-error {
  display: flex;
  flex-direction: column;
}
</style>
