<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import translatedStringFromTS from './_ts_file_using_i18n'

defineProps<{ screenshotMode: boolean }>()

const { _t, _tn, switchLanguage, translationLoading } = usei18n()

const appleCount = ref('0')
const name = ref<string>('Alice')
</script>

<template>
  <label>
    <CmkButton @click="switchLanguage('en')">{{ _t('English') }}</CmkButton>
  </label>
  <label>
    <CmkButton @click="switchLanguage('de')">{{ _t('German') }}</CmkButton>
  </label>
  <label>
    <CmkButton @click="switchLanguage('fr')">{{ _t('French') }}</CmkButton>
  </label>

  <br />
  <label>
    {{ translationLoading ? _t('Loading translations...') : _t('Translations loaded') }}
  </label>
  <br />
  <label>
    {{ _t('Your name') }}
    <CmkInput v-model="name" />
  </label>
  <br />
  <label>
    {{ _t('Number of apples') }}
    <CmkDropdown
      v-model:selected-option="appleCount"
      :options="{
        type: 'fixed',
        suggestions: [
          { title: '0', name: '0' },
          { title: '1', name: '1' },
          { title: '3', name: '3' }
        ]
      }"
      label=""
    />
  </label>
  <br />
  <br />
  <CmkParagraph> {{ _t('Hello %{name}!', { name }) }}</CmkParagraph>
  <CmkParagraph>
    {{
      _tn('There is %{ n } apple', 'There are %{ n } apples', parseInt(appleCount), {
        n: appleCount
      })
    }}</CmkParagraph
  >
  <br />
  <CmkParagraph>{{ translatedStringFromTS }}</CmkParagraph>
</template>

<style scoped></style>
