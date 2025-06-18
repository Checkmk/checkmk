<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAccordion from '@/components/CmkAccordion/CmkAccordion.vue'
import { ref } from 'vue'
import type { CmkIconProps } from '../CmkIcon.vue'
import CmkDropdown from '../CmkDropdown.vue'
import CmkAccordionItem from '../CmkAccordion/CmkAccordionItem.vue'
import CmkIcon from '../CmkIcon.vue'
import CmkButton from '../CmkButton.vue'

defineProps<{ screenshotMode: boolean }>()

const openedItems = ref<string[]>(['item-3'])
const renderRef = ref<boolean>(true)

const items: {
  id: string
  header: {
    title: string
    icon: CmkIconProps
  }
  disabled?: boolean
  content: string
}[] = [
  {
    id: 'item-1',
    header: {
      title: 'Item 1',
      icon: {
        name: 'search'
      }
    },
    content: 'This is the 1st Item'
  },
  {
    id: 'item-2',
    disabled: true,
    header: {
      title: 'Item 2 (disabled)',
      icon: {
        name: 'close'
      }
    },
    content: 'This is the 2nd Item'
  },
  {
    id: 'item-3',
    header: {
      title: 'Item 3',
      icon: {
        name: 'info-circle'
      }
    },
    content: 'This is the 3rd Item'
  },
  {
    id: 'last-item',
    header: {
      title: 'The last item',
      icon: {
        name: 'info-circle'
      }
    },
    content: 'This is the 3rd Item'
  }
]

const minOpenSelected = ref<'0' | '1' | '2'>('1')
const maxOpenSelected = ref<'1' | '2' | '3'>('1')
</script>

<template>
  <div>
    <label>min. opened:</label>
    <CmkDropdown
      v-model:selected-option="minOpenSelected"
      :options="{
        type: 'fixed',

        suggestions: [
          { name: '0', title: '0' },
          { name: '1', title: '1' },
          { name: '2', title: '2' }
        ]
      }"
      component-id="min-opened"
      label="Accordion min opened"
    />
  </div>

  <div>
    <label>max. opened:</label>
    <CmkDropdown
      v-model:selected-option="maxOpenSelected"
      :options="{
        type: 'fixed',
        suggestions: [
          { name: '0', title: '0 (unlimited)' },
          { name: '1', title: '1' },
          { name: '2', title: '2' },
          { name: '3', title: '3' }
        ]
      }"
      component-id="max-opened"
      label="Accordion max opened"
    />
  </div>

  <CmkButton
    @click="
      () => {
        if (openedItems.indexOf('item-1') >= 0) {
          delete openedItems[openedItems.indexOf('item-1')]
          openedItems = openedItems.filter((e) => e)
        } else {
          openedItems.push('item-1')
        }
      }
    "
    >Toggle Item-1 from outside Accordion</CmkButton
  >

  <br /><br /><br />
  <CmkAccordion
    v-if="renderRef === true"
    v-model="openedItems"
    :max-open="parseInt(maxOpenSelected)"
    :min-open="parseInt(minOpenSelected)"
    class="cmk-demo-accordion"
  >
    <CmkAccordionItem
      v-for="item in items"
      :key="item.id"
      :value="item.id"
      :disabled="item.disabled"
    >
      <template #header>
        <CmkIcon :name="item.header.icon.name" class="demo-accordion-header-icon"></CmkIcon>
        <h2 class="demo-accordion-header-title">
          {{ item.header.title }}
        </h2>
      </template>
      <template #content>
        <div v-if="item.id === 'item-1'" class="additional-div">
          This is only rendered in item 1
        </div>
        {{ item.content }}
      </template>
    </CmkAccordionItem>
  </CmkAccordion>

  <br /><br />
  <label>Currently opened items:</label><br /><br />
  <code>{{ openedItems }}</code>
</template>

<style scoped>
.demo-accordion-header-icon {
  margin-right: 16px;
}

.demo-accordion-header-title {
  margin: 0;
}

.additional-div {
  background: red;
  padding: 16px;
  margin: 0 0 16px 0;
}

div:has(> label) {
  padding: 8px 0;
}

label {
  width: 200px;
  display: inline-block;
}
</style>
