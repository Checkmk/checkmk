<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import FormEdit from '@/form/components/FormEdit.vue'
import { type FormSpecWidgetProps } from './widget_types'
import type { ValidationMessages } from '@/form'

const props = defineProps<FormSpecWidgetProps>()
const emit = defineEmits(['update'])

const formSpecId = props.form_spec.id as string
const internal = ref(props?.data![formSpecId] || props.form_spec.data || {})

const validationErrors = computed((): ValidationMessages => {
  const errors = props?.errors![formSpecId] || []
  return errors
})

//This will set a starting value on the quick setup component for this form spec
emit('update', formSpecId, internal)

watch(internal.value, (newValue) => {
  emit('update', formSpecId, newValue)
})
</script>

<template>
  <table class="qs-formspec-widget">
    <tr>
      <td>
        <FormEdit
          v-model:data="internal"
          :spec="form_spec.spec"
          :backend-validation="validationErrors"
        />
      </td>
    </tr>
  </table>
</template>

<style scoped>
table.qs-formspec-widget {
  border-spacing: 0;
}
</style>
