<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'

import CmkIcon from '@/components/CmkIcon'

import { type ValidationMessages } from '@/form/private/validation'

import FormMultilineText from './FormMultilineText.vue'

const props = defineProps<{
  spec: FormSpec.CommentTextArea
  backendValidation: ValidationMessages
}>()

const data = defineModel<string>('data', { required: true })

const prependDateAndUsername = (): void => {
  const date = new Date()
  const formattedDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  data.value = `${formattedDate} ${props.spec.user_name || ''}:\n${data.value}`
}
</script>
<template>
  <div class="form-comment-text-area">
    <FormMultilineText
      v-model:data="data"
      :backend-validation="backendValidation"
      :spec="{ ...spec, type: 'multiline_text' }"
    />
    <CmkIcon
      :title="props.spec.i18n.prefix_date_and_comment"
      name="insertdate"
      size="xlarge"
      :style="{
        cursor: 'pointer',
        'margin-left': 'var(--spacing)'
      }"
      @click="prependDateAndUsername()"
    />
  </div>
</template>

<style scoped>
.form-comment-text-area {
  display: flex;
}
</style>
