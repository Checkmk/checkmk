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
  <table class="ucl-accessibility-table__table" aria-label="Keyboard accessibility">
    <thead>
      <tr>
        <th><CmkHeading type="h4">Key</CmkHeading></th>
        <th><CmkHeading type="h4">Description</CmkHeading></th>
      </tr>
    </thead>
    <tbody v-if="normalizedData.length">
      <tr v-for="item in normalizedData" :key="item.description">
        <td>
          <template v-for="(group, groupIdx) in item.keys" :key="`${groupIdx}-${group.join('+')}`">
            <span v-if="groupIdx > 0" class="ucl-accessibility-table__key-separator">or</span>
            <span v-for="(keyName, keyIdx) in group" :key="`${keyIdx}-${keyName}`">
              <span class="ucl-accessibility-table__key-pill">{{ keyName }}</span>
              <span v-if="keyIdx < group.length - 1" class="ucl-accessibility-table__key-separator"
                >+</span
              >
            </span>
          </template>
        </td>
        <td>
          {{ item.description }}
        </td>
      </tr>
    </tbody>
    <tbody v-else>
      <tr class="ucl-accessibility-table__empty-message">
        <td colspan="2">No keyboard accessibility available for this component</td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.ucl-accessibility-table__table {
  background: var(--ucl-detail-section-bg-color);
  width: 100%;
  margin-bottom: var(--spacing);
  border-collapse: separate;
  border-spacing: 0;

  td,
  th {
    padding: 12px 16px;
    text-align: left;
    align-items: center;
    color: var(--ucl-body-text-color);
  }

  tr th,
  tr td {
    border-bottom: 1px solid var(--ucl-elements-border-color);
  }

  tr th {
    border-top: 1px solid var(--ucl-elements-border-color);
    background: var(--ucl-elements-background-color);
  }

  tr th:last-child,
  tr td:last-child {
    border-right: 1px solid var(--ucl-elements-border-color);
  }

  tr td:first-child,
  tr th:first-child {
    border-left: 1px solid var(--ucl-elements-border-color);
  }

  tr:first-child th:first-child {
    border-top-left-radius: 8px;
  }

  tr:first-child th:last-child {
    border-top-right-radius: 8px;
  }

  tr:last-child td:first-child {
    border-bottom-left-radius: 8px;
  }

  tr:last-child td:last-child {
    border-bottom-right-radius: 8px;
  }
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
