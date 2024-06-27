<script setup lang="ts">
import { ref } from 'vue'
import CollapsibleTitle from '../element/CollapsibleTitle.vue'
import CompositeWidget from './CompositeWidget.vue'
import { type CollapsibleWidgetProps } from './widget_types'

const props = defineProps<CollapsibleWidgetProps>()
defineEmits(['update'])

const isOpen = ref(!!props.open)

const toggleOpen = () => {
  isOpen.value = !isOpen.value
}
</script>

<template>
  <CollapsibleTitle :label="props.label" :open="isOpen" @toggle-open="toggleOpen" />
  <CompositeWidget v-if="isOpen" :components="props.components" @update="$emit('update')" />
</template>

<style scoped></style>
