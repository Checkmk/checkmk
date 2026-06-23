<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Dictionary, StaticText } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkDropdown from '@/components/CmkDropdown'
import type { Suggestions } from '@/components/CmkSuggestions'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import FormEdit from '@/form/FormEdit.vue'
import FormStaticText from '@/form/private/forms/FormStaticText.vue'

defineProps<{ screenshotMode: boolean }>()

const ALERT_TEXT = 'The URL will be generated automatically after you save the form.'
const URL_TEXT = 'https://mycheckmk.example.com/saml_metadata.py'

const STYLE_OPTIONS: Suggestions = {
  type: 'fixed',
  suggestions: [
    { name: 'text', title: 'text' },
    { name: 'preformatted', title: 'preformatted' },
    { name: 'alert_info', title: 'alert_info' },
    { name: 'alert_warning', title: 'alert_warning' },
    { name: 'alert_error', title: 'alert_error' }
  ]
}
const selectedStyle = ref<string | null>('alert_info')

const standaloneSpec = computed<StaticText>(() => ({
  type: 'static_text',
  title: 'Metadata endpoint',
  help: 'A read-only value shown inside the form.',
  validators: [],
  value: '',
  style: (selectedStyle.value ?? 'text') as StaticText['style']
}))
const standaloneData = ref<string>(ALERT_TEXT)

function staticText(title: string, style: StaticText['style']): StaticText {
  return {
    type: 'static_text',
    title,
    help: '',
    validators: [],
    value: '',
    style
  }
}

const dictionarySpec: Dictionary = {
  type: 'dictionary',
  title: '',
  help: '',
  validators: [],
  no_elements_text: '(no parameters)',
  groups: [],
  additional_static_elements: {},
  elements: [
    {
      name: 'metadata_endpoint',
      required: true,
      render_only: false,
      group: null,
      default_value: ALERT_TEXT,
      parameter_form: staticText('Metadata endpoint', 'alert_info')
    },
    {
      name: 'acs_endpoint',
      required: true,
      render_only: false,
      group: null,
      default_value: URL_TEXT,
      parameter_form: staticText('Assertion Consumer Service endpoint', 'text')
    }
  ]
} as Dictionary

const dictionaryData = ref<Record<string, string>>({
  metadata_endpoint: ALERT_TEXT,
  acs_endpoint: URL_TEXT
})
</script>

<template>
  <div>
    <CmkDropdown
      v-model="selectedStyle"
      :options="STYLE_OPTIONS"
      input-hint="Select a style"
      no-results-hint="No styles"
      label="style"
      required
    />
  </div>
  <CmkHeading type="h4">Standalone</CmkHeading>
  <FormStaticText v-model:data="standaloneData" :spec="standaloneSpec" :backend-validation="[]" />
  <CmkHeading type="h4">Alert Example Inside a Dictionary</CmkHeading>
  <FormEdit v-model:data="dictionaryData" :spec="dictionarySpec" :backend-validation="[]" />
</template>
