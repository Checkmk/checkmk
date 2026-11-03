<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import type { DataBackendSettings } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed } from 'vue'

import FormDictionary from '@/form/private/forms/FormDictionary/FormDictionary.vue'
import type { ValidationMessages } from '@/form/private/validation'

import CentralConnectionTest from './CentralConnectionTest.vue'
import {
  ADDRESS_SEEN_BY_CENTRAL,
  centrallyRoutedFeatures,
  dictionaryOf,
  placesAFeatureCentrally
} from './settings'

const props = defineProps<{
  spec: DataBackendSettings
  backendValidation: ValidationMessages
}>()

const data = defineModel<Record<string, unknown>>('data', { required: true })

// FormDictionary fixes its elements on mount, so the address needs its own
const settings = computed(() =>
  dictionaryOf(props.spec, (name) => name !== ADDRESS_SEEN_BY_CENTRAL)
)
const address = computed(() => dictionaryOf(props.spec, (name) => name === ADDRESS_SEEN_BY_CENTRAL))
const showAddress = computed(() => placesAFeatureCentrally(props.spec, data.value))

const remoteSettings = computed(() => {
  const enteredAddress = data.value[ADDRESS_SEEN_BY_CENTRAL] as string | undefined
  return {
    centrally_routed_features: centrallyRoutedFeatures(props.spec, data.value) as Array<
      components['schemas']['FeatureName']
    >,
    ...(enteredAddress ? { address_seen_by_central: enteredAddress } : {})
  }
})

const settingsValidation = computed(() =>
  props.backendValidation.filter((message) => message.location[0] !== ADDRESS_SEEN_BY_CENTRAL)
)
const addressValidation = computed(() =>
  props.backendValidation.filter((message) => message.location[0] === ADDRESS_SEEN_BY_CENTRAL)
)
</script>

<template>
  <FormDictionary v-model:data="data" :spec="settings" :backend-validation="settingsValidation" />
  <FormDictionary
    v-if="showAddress"
    v-model:data="data"
    :spec="address"
    :backend-validation="addressValidation"
  />
  <CentralConnectionTest
    v-if="showAddress && props.spec.connection_test_site_id !== null"
    :site-id="props.spec.connection_test_site_id"
    :settings="remoteSettings"
  />
</template>
