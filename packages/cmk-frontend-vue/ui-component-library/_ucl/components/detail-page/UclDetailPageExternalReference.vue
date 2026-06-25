<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCode from '@/components/CmkCode.vue'
import CmkCopy from '@/components/CmkCopy.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkLink from '@/components/CmkLink.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

export interface ExternalReferenceItem {
  label: string
  description: string
  href?: string
  command?: string
  file?: string
}

withDefaults(
  defineProps<{
    title?: string
    data: ExternalReferenceItem[]
  }>(),
  {
    title: 'External references'
  }
)

const GITHUB_BLOB_BASE = 'https://github.com/Checkmk/checkmk/blob/master/'

function githubUrl(file: string): string {
  return `${GITHUB_BLOB_BASE}${file.replace(/^\/+/, '')}`
}
</script>

<template>
  <div class="ucl-detail-page-external-reference__section">
    <CmkHeading type="h2">{{ title }}</CmkHeading>
    <table class="ucl-detail-page-external-reference__table" aria-label="External references">
      <thead>
        <tr>
          <th><CmkHeading type="h4">Reference</CmkHeading></th>
          <th><CmkHeading type="h4">Link / command</CmkHeading></th>
          <th><CmkHeading type="h4">Description</CmkHeading></th>
        </tr>
      </thead>
      <tbody v-if="data.length">
        <tr v-for="item in data" :key="item.label">
          <td>{{ item.label }}</td>
          <td>
            <div v-if="item.file" class="ucl-detail-page-external-reference__file">
              <CmkLink :href="githubUrl(item.file)" target="_blank">
                <code>{{ item.file }}</code>
                <CmkIcon name="export-link" size="small" />
              </CmkLink>
              <CmkCopy :text="item.file">
                <button
                  type="button"
                  class="ucl-detail-page-external-reference__copy"
                  aria-label="Copy file path"
                >
                  <CmkIcon name="view-copy" size="small" />
                </button>
              </CmkCopy>
            </div>
            <CmkLink v-else-if="item.href" :href="item.href" target="_blank">
              {{ item.href }}
              <CmkIcon name="export-link" size="small" />
            </CmkLink>
            <CmkCode v-else-if="item.command" :code-text="item.command" />
          </td>
          <td>{{ item.description }}</td>
        </tr>
      </tbody>
      <tbody v-else>
        <tr class="ucl-detail-page-external-reference__empty-message">
          <td colspan="3">No external references available</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.ucl-detail-page-external-reference__section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
}

.ucl-detail-page-external-reference__table {
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

.ucl-detail-page-external-reference__file {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
}

.ucl-detail-page-external-reference__copy {
  display: inline-flex;
  align-items: center;
  padding: var(--dimension-2);
  border: 1px solid transparent;
  border-radius: var(--dimension-2);
  background: transparent;
  color: var(--ucl-body-text-color);
  cursor: pointer;
}

.ucl-detail-page-external-reference__copy:hover,
.ucl-detail-page-external-reference__copy:focus-visible {
  border-color: var(--success);
  outline: none;
}

.ucl-detail-page-external-reference__empty-message {
  padding: 12px 16px;
  color: var(--ucl-body-text-color);
  text-align: center;
  font-style: italic;
}
</style>
