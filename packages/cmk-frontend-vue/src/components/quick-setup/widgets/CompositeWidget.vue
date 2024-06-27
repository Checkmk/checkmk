<script setup lang="ts">
import { type CompositeWidgetProps } from './widget_types'
import { getWidget } from './utils'

const props = defineProps<CompositeWidgetProps>()
const emit = defineEmits(['update'])

const update_data = (id: string, value: object) => {
  emit('update', id, value)
}
</script>

<template>
  <div v-for="({ widget_type, ...widget_props }, idx) in props.components" :key="idx">
    <component :is="getWidget(widget_type)" v-bind="widget_props" @update="update_data" />
  </div>
</template>

<style scoped></style>
