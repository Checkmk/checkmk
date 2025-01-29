<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type FormSpecWidgetProps } from './widget_types'
import FormReadonly from '@/form/components/FormReadonly.vue'

defineProps<FormSpecWidgetProps>()
</script>

<template>
  <table class="qs-formspec-recap-widget">
    <tbody>
      <tr>
        <td>
          <FormReadonly :data="form_spec.data" :spec="form_spec.spec" :backend-validation="[]" />
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
table.qs-formspec-recap-widget {
  border-spacing: 0;
}
</style>
