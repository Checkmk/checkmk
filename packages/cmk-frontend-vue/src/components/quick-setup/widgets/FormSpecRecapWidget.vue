<script setup lang="ts">
import { type FormSpecWidgetProps } from './widget_types'
import FormReadonly from '@/components/cmk-form/FormReadonly.vue'

defineProps<FormSpecWidgetProps>()
</script>

<template>
  <table class="nform">
    <tr>
      <td>
        <FormReadonly :data="form_spec.data" :spec="form_spec.spec" :backend-validation="[]" />
      </td>
    </tr>
  </table>
</template>
