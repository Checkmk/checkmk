<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import FormEdit from '@/form/components/FormEdit.vue'
import { type FormSpecWidgetProps } from './widget_types'
import type { ValidationMessages } from '@/lib/validation'

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
  <table class="nform">
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
