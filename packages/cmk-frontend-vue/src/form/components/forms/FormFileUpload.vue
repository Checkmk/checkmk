<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { FileUpload } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import { useId } from '@/form/utils'
import CmkButton from '@/components/CmkButton.vue'
import FormValidation from '@/form/components/FormValidation.vue'

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
    <input v-if="value.file_name === null" :id="componentId" :name="data.input_uuid" type="file" />
    <div v-if="value.file_name" class="replace">
      <CmkButton variant="secondary" size="small" @click="value.file_name = null">{{
        spec.i18n.replace_file
      }}</CmkButton>
      <label class="filename"> {{ value.file_name }}</label>
    </div>
    <FormValidation :validation="validation"></FormValidation>
  </span>
</template>

<style scoped>
div.replace {
  cursor: pointer;
  margin-bottom: -8px;

  label.filename {
    padding-left: 10px;
  }
}
</style>
