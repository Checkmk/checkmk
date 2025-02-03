<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'
import { type Folder } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormValidation from '@/form/components/FormValidation.vue'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'

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
    <input
      v-model="value"
      :placeholder="spec.input_hint || ''"
      :aria-label="spec.title"
      type="text"
      size="27"
    />
  </span>
  <FormValidation :validation="validation"></FormValidation>
</template>

<style scoped>
.form-folder {
  display: flex;
  width: fit-content;
  height: 15px;
  padding: 0 6px 6px;
  align-items: baseline;
  background-color: var(--default-form-element-bg-color);
  border-radius: var(--border-radius);

  img {
    position: relative;
    top: 1px;
  }

  span {
    z-index: 1;
    position: relative;
    right: -6px;
  }
}
</style>
