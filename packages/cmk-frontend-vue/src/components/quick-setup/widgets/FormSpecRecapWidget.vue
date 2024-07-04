<script setup lang="ts">
import { type FormSpecWidgetProps } from './widget_types'
import CmkFormReadonly from '@/components/cmk-form/CmkFormReadonly.vue'

defineProps<FormSpecWidgetProps>()
</script>

<template>
  <table class="nform">
    <tr>
      <td>
        <CmkFormReadonly :data="form_spec.data" :spec="form_spec.spec" :backend-validation="[]" />
      </td>
    </tr>
  </table>
</template>
