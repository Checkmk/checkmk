<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Folder } from 'cmk-shared-typing/typescript/vue_formspec_components'

import CmkIcon from '@/components/CmkIcon.vue'
import FormValidation from '@/form/components/FormValidation.vue'
import { inputSizes } from '@/form/components/utils/sizes'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import FormAutocompleter from '@/form/private/FormAutocompleter.vue'

const props = defineProps<{
  spec: Folder
  backendValidation: ValidationMessages
}>()

const data = defineModel<string>('data', { required: true })
const [validation, value] = useValidation<string>(
  data,
  props.spec.validators,
  () => props.backendValidation
)
</script>

<template>
  <span class="form-folder">
    <CmkIcon name="folder_blue" size="small" />
    <span>Main/</span>
    <FormAutocompleter
      v-model="value"
      :size="inputSizes['MEDIUM'].width"
      :autocompleter="spec.autocompleter"
      :placeholder="spec.input_hint ?? ''"
      :aria-label="spec.title"
      :filter-on="['@main']"
      :reset-input-on-add="false"
      :allow-new-value-input="spec.allow_new_folder_path"
    />
  </span>
  <FormValidation :validation="validation"></FormValidation>
</template>

<style scoped>
.form-folder {
  display: flex;
  align-items: center;
  width: fit-content;
  height: 15px;
  padding: 4px 0 4px 6px;
  background-color: var(--default-form-element-bg-color);
  border-radius: var(--border-radius);

  span {
    z-index: 1;
    position: relative;
    right: -3px;
    margin-left: 2px;
  }
}
</style>
