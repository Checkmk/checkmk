<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type CompositeWidgetProps } from './widget_types'
import { getGetWidget } from '@/quick-setup/components/quick-setup/utils'
const getWidget = getGetWidget()

const props = defineProps<CompositeWidgetProps>()
const emit = defineEmits(['update'])

const updateData = (id: string, value: object) => emit('update', id, value)
</script>

<template>
  <div v-for="({ widget_type, ...widget_props }, idx) in props.items" :key="idx">
    <component
      :is="getWidget(widget_type)"
      v-bind="widget_props"
      :data="props.data"
      :errors="props.errors"
      @update="updateData"
    />
  </div>
</template>

<style scoped></style>
