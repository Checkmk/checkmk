<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { AccordionContent, AccordionHeader, AccordionItem } from 'radix-vue'
import CmkAccordionTrigger from './CmkAccordionTrigger.vue'

export interface CmkAccordionItemProps {
  value: string
  disabled?: boolean | undefined
}

const props = defineProps<CmkAccordionItemProps>()
</script>

<template>
  <AccordionItem :value="props.value" :disabled="props.disabled" class="cmk-accordion-item">
    <AccordionHeader as="div" class="cmk-accordion-item-header"
      ><CmkAccordionTrigger :value="value" :disabled="disabled ? true : false">
        <slot name="header" />
      </CmkAccordionTrigger>
    </AccordionHeader>
    <AccordionContent class="cmk-accordion-item-content">
      <div class="cmk-accordion-item-content-wrapper">
        <slot name="content" />
      </div>
    </AccordionContent>
  </AccordionItem>
</template>

<style scoped>
.cmk-accordion-item {
  display: flex;
  flex-direction: column;
  border: 1px solid transparent;
  background: var(--ux-theme-3);
  border-radius: 4px;
  overflow: hidden;
  width: 100%;
  margin-bottom: 8px;

  &[data-state='open'] {
    border: 1px solid var(--success);
    background: var(--ux-theme-5);
  }

  &:last-of-type {
    margin-bottom: 0;
  }
}

.cmk-accordion-item-content-wrapper {
  padding: 16px;
  overflow: hidden;
}

.cmk-accordion-item-header {
  padding: 8px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  width: calc(100% -32px);
  border-bottom: 1px transparent;
  border-radius: 4px;
  position: relative;

  &:hover {
    background: var(--ux-theme-6);
  }

  &[data-state='open'] {
    border-bottom: 1px solid var(--success);
    border-radius: 4px 4px 0 0;
  }
}

.cmk-accordion-item-content {
  &:focus-within {
    position: relative;
    z-index: 1;
  }

  &[data-state='open'] {
    animation: slideDown 0.5s ease-in-out;
  }

  &[data-state='closed'] {
    animation: slideUp 0.5s ease-in-out;
  }
}

@keyframes slideDown {
  from {
    opacity: 0;
    height: 0;
  }
  to {
    opacity: 1;
    height: var(--radix-accordion-content-height);
  }
}

@keyframes slideUp {
  from {
    opacity: 1;
    height: var(--radix-accordion-content-height);
  }
  to {
    opacity: 0;
    height: 0;
  }
}

/* Disabled Styling */
.cmk-accordion-item[data-disabled] {
  opacity: 0.7;
  cursor: default;

  .cmk-accordion-item-header[data-disabled]:hover {
    background: transparent;
  }
}
</style>
