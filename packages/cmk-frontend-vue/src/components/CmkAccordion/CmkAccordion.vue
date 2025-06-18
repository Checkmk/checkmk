<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { AccordionRoot } from 'radix-vue'
import { provide } from 'vue'
import { triggerItemKey } from './trigger-item'

export interface CmkAccordionProps {
  minOpen?: number
  maxOpen?: number
}

provide(triggerItemKey, toggleItem)

const openedItems = defineModel<string[]>({ required: true })
const { minOpen = 1, maxOpen = 1 } = defineProps<CmkAccordionProps>()

function toggleItem(id: string): void {
  let opened: string[] = openedItems.value.slice(0)

  let maxO = maxOpen
  if (maxO > 0 && maxO < minOpen) {
    maxO = minOpen
  }

  const index = opened.indexOf(id)
  if (index >= 0) {
    if (opened.length > minOpen) {
      delete opened[index]
      opened = opened.filter((e) => e)
    }
  } else {
    opened.push(id)
    if (maxO && opened.length > maxO) {
      opened.shift()
    }
  }

  openedItems.value = opened
}
</script>

<template>
  <AccordionRoot
    v-model="openedItems"
    orientation="vertical"
    :collapsible="minOpen === 0"
    class="cmk-accordion-root"
  >
    <slot />
  </AccordionRoot>
</template>

<style scoped>
.cmk-accordion-root {
  display: flex;
  flex-direction: column;
  width: 100%;
}
</style>
