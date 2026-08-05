<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import ScheduleDowntimeForm, {
  type ScheduleDowntimeFormValues
} from '@/monitoring/shared/components/action/actions/ScheduleDowntimeForm.vue'

const model = defineModel<ScheduleDowntimeFormValues>({ required: true })

const emit = defineEmits<{
  (event: 'update:valid', valid: boolean): void
}>()
</script>

<template>
  <ScheduleDowntimeForm
    v-model="model"
    target-kind="service"
    @update:valid="emit('update:valid', $event)"
  />
</template>
