<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watch, type Ref } from 'vue'
import CollapsibleTitle from '@/quick-setup/components/CollapsibleTitle.vue'
import CompositeWidget from './CompositeWidget.vue'
import { type CollapsibleWidgetProps } from './widget_types'

const props = defineProps<CollapsibleWidgetProps>()
const emits = defineEmits(['update'])

const isOpen = ref(!!props?.open)

const toggleOpen = () => {
  isOpen.value = !isOpen.value
}

watch(props, (newProps) => {
  if (Object.keys(newProps?.errors || {}).length > 0) {
    isOpen.value = true
  }
})

const updateData = (id: string, value: Ref) => {
  if (Object.keys(value.value || {}).length > 0) {
    isOpen.value = true
  }
  emits('update', id, value)
}
</script>

<template>
  <CollapsibleTitle
    :title="props.title"
    :help_text="props.help_text"
    :open="isOpen"
    @toggle-open="toggleOpen"
  />
  <div v-show="isOpen">
    <CompositeWidget
      :items="props.items"
      :data="props?.data || {}"
      :errors="props.errors || {}"
      @update="updateData"
    />
  </div>
</template>

<style scoped></style>
