<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CompositeWidget from '@/quick-setup/components/quick-setup/widgets/CompositeWidget.vue'
import type { ConditionalNotificationStageWidgetProps } from '@/quick-setup/components/quick-setup/widgets/widget_types'

const props = defineProps<ConditionalNotificationStageWidgetProps>()
const emits = defineEmits(['update'])

const updateData = (id: string, value: object) => {
  emits('update', id, value)
}
</script>

<template>
  <div v-if="props.condition">
    <CompositeWidget
      :items="props.items"
      :data="props?.data || {}"
      :errors="props.errors || {}"
      @update="updateData"
    />
  </div>
</template>
