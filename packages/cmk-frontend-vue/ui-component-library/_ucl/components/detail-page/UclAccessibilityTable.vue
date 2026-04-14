<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import CmkHeading from '@/components/typography/CmkHeading.vue'

export interface AccessibilityItem {
  keys: (string | string[])[]
  description: string
}

const props = defineProps<{ data: AccessibilityItem[] }>()

const normalizedData = computed(() =>
  props.data.map(({ keys, description }) => ({
    description,
    keys: keys.map((k) => (Array.isArray(k) ? k : [k]))
  }))
)
</script>

<template>
  <div class="ucl-accessibility-table__table" role="table" aria-label="Keyboard accessibility">
    <div class="ucl-accessibility-table__table-header" role="row">
      <CmkHeading type="h4" role="columnheader">Key</CmkHeading>
      <CmkHeading type="h4" role="columnheader">Description</CmkHeading>
    </div>
    <template v-if="normalizedData.length">
      <div
        v-for="item in normalizedData"
        :key="item.description"
        class="ucl-accessibility-table__table-row"
        role="row"
      >
        <div class="ucl-accessibility-table__table-cell" role="cell">
          <template v-for="(group, groupIdx) in item.keys" :key="`${groupIdx}-${group.join('+')}`">
            <span v-if="groupIdx > 0" class="ucl-accessibility-table__key-separator">or</span>
            <span class="ucl-accessibility-table__key-group">
              <template v-for="(keyName, keyIdx) in group" :key="`${keyIdx}-${keyName}`">
                <span class="ucl-accessibility-table__key-pill">{{ keyName }}</span>
                <span
                  v-if="keyIdx < group.length - 1"
                  class="ucl-accessibility-table__key-separator"
                  >+</span
                >
              </template>
            </span>
          </template>
        </div>
        <div class="ucl-accessibility-table__table-cell" role="cell">
          {{ item.description }}
        </div>
      </div>
    </template>
    <div v-else class="ucl-accessibility-table__empty-message" role="row">
      <div role="cell" colspan="2">No keyboard accessibility available for this component</div>
    </div>
  </div>
</template>

<style scoped>
.ucl-accessibility-table__table {
  border: 1px solid var(--ucl-elements-border-color);
  background: var(--ucl-detail-section-bg-color);
  border-radius: 8px;
  width: 100%;
  margin-bottom: var(--spacing);
}

.ucl-accessibility-table__table-header {
  display: flex;
  background: var(--ucl-elements-background-color);
  border-bottom: 1px solid var(--ucl-elements-border-color);
}

.ucl-accessibility-table__table-header > * {
  flex: 1;
  padding: 12px 16px;
  text-align: left;
}

.ucl-accessibility-table__table-row {
  display: flex;
  border-top: 1px solid var(--ucl-elements-border-color);
}

.ucl-accessibility-table__table-cell {
  flex: 1;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: var(--spacing-half);
  color: var(--ucl-body-text-color);
}

.ucl-accessibility-table__key-group {
  display: inline-flex;
  align-items: center;
}

.ucl-accessibility-table__key-separator {
  margin: 0 6px;
  color: var(--ucl-body-text-color);
}

.ucl-accessibility-table__key-pill {
  background: var(--ucl-detail-table-pill-bg-color);
  border-radius: 4px;
  margin: 2px 0;
  padding: 4px 8px;
  color: var(--ucl-cta-banner-title-color);
  display: inline-block;
}

.ucl-accessibility-table__empty-message {
  padding: 12px 16px;
  color: var(--ucl-body-text-color);
  text-align: center;
  font-style: italic;
}
</style>
