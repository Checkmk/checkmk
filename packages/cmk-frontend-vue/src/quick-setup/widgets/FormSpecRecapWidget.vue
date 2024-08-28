<script setup lang="ts">
import { type FormSpecWidgetProps } from './widget_types'
import FormReadonly from '@/form/components/FormReadonly.vue'

defineProps<FormSpecWidgetProps>()
</script>

<template>
  <table class="qs-formspec-recap-widget">
    <tr>
      <td>
        <FormReadonly :data="form_spec.data" :spec="form_spec.spec" :backend-validation="[]" />
      </td>
    </tr>
  </table>
</template>

<style scoped>
table.qs-formspec-recap-widget {
  border-spacing: 0;
}
</style>
