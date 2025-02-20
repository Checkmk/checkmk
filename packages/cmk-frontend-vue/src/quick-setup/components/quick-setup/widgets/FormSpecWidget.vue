<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'
import FormEdit from '@/form/components/FormEdit.vue'
import { type FormSpecWidgetProps } from './widget_types'
import type { ValidationMessages } from '@/form'
import HelpText from '@/components/HelpText.vue'

const props = defineProps<FormSpecWidgetProps>()
const emit = defineEmits(['update'])

const formSpecId = props.form_spec.id as string
const internal = ref<unknown>(props?.data![formSpecId] || props.form_spec.data || {})

const validationErrors = computed((): ValidationMessages => {
  const errors = props?.errors![formSpecId] || []
  return errors
})

//This will set a starting value on the quick setup component for this form spec
emit('update', formSpecId, internal)

function formEditDataWasUpdated(newValue: unknown) {
  internal.value = newValue
  emit('update', formSpecId, newValue)
}
</script>

<template>
  <table class="qs-formspec-widget">
    <tbody>
      <tr>
        <td>
          <HelpText :help="form_spec.spec.help" />
          <FormEdit
            :data="internal"
            :spec="form_spec.spec"
            :backend-validation="validationErrors"
            @update:data="formEditDataWasUpdated"
          />
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
table.qs-formspec-widget {
  border-spacing: 0;
}
</style>
