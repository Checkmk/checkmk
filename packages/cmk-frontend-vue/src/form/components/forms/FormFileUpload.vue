<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { FileUpload } from 'cmk-shared-typing/typescript/vue_formspec_components'

import CmkButton from '@/components/CmkButton.vue'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'

import { type ValidationMessages, useValidation } from '@/form/components/utils/validation'
import FormLabel from '@/form/private/FormLabel.vue'
import { useId } from '@/form/utils'

const props = defineProps<{
  spec: FileUpload
  backendValidation: ValidationMessages
}>()

type FileUploadData = {
  input_uuid: string
  file_name: string | null
  file_type: string | null
  file_content_encrypted: string | null
}

const data = defineModel<FileUploadData>('data', { required: true })
const [validation, value] = useValidation<FileUploadData>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const componentId = useId()
</script>

<template>
  <span>
    <input
      v-if="value.file_name === null"
      :id="componentId"
      :name="data.input_uuid"
      type="file"
      :aria-label="spec.title"
    />
    <div v-if="value.file_name" class="form-file-upload__replace">
      <CmkButton @click="value.file_name = null">{{ spec.i18n.replace_file }}</CmkButton>
      <FormLabel class="form-file-upload__filename"> {{ value.file_name }}</FormLabel>
    </div>
    <FormValidation :validation="validation"></FormValidation>
  </span>
</template>

<style scoped>
.form-file-upload__replace {
  cursor: pointer;
  margin-bottom: -8px;
}

.form-file-upload__filename {
  padding-left: 10px;
}
</style>
