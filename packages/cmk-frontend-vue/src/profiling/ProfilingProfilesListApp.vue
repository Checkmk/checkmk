<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
/*
 * Upload flow: the actual <form> and <input type="file"> elements are
 * rendered by the Python `_render_upload_form` helper so the existing
 * Checkmk upload handling (CSRF token, multipart parsing, redirect) keeps
 * working unchanged. This component attaches drag-and-drop UI to the
 * Python-rendered form via `document.getElementById` in onMounted. A future
 * refactor would move the upload to a REST endpoint and own the <input> here.
 */
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkBadge from 'cmk-ui-library/components/CmkBadge.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkIconLink from 'cmk-ui-library/components/CmkIconLink.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useDebounceFn } from 'cmk-ui-library/lib/useDebounce'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

import { useSortedRows } from './composables/useSortedRows'
import type { ProfileMetadata, ProfileSourceType } from './types'
import { formatFileSize, formatMs, formatTimestamp } from './utils/format'

type SortKey = 'timestamp' | 'source_type' | 'source_info' | 'duration_ms'
type ProfileRow = ProfileMetadata & {
  flamegraph_url: string
  download_url: string
  delete_url: string
}

const props = defineProps<{
  profiles: ProfileRow[]
  upload_form_id: string
  upload_input_id: string
  upload_error: string
}>()

const { _t } = usei18n()

function sourceLabel(source: ProfileSourceType): string {
  switch (source) {
    case 'gui_request':
      return _t('GUI request')
    case 'file_upload':
      return _t('Upload')
    case 'base_command':
      return _t('cmk --profile')
  }
}

/* Search (filters source_info / type label before sort + pagination) */
const searchValue = ref('')
const searchQuery = ref('')
const syncSearch = useDebounceFn((v: string) => {
  searchQuery.value = v
}, 120)
watch(searchValue, (v) => syncSearch(v))

function clearSearch() {
  searchValue.value = ''
  searchQuery.value = ''
}

// Precompute the source-type label so the filter callback doesn't call
// sourceLabel() per row per keystroke. The map only rebuilds when the source
// profiles array changes, not on every search keystroke.
const labeledProfiles = computed(() =>
  props.profiles.map((p) => ({ ...p, _label: sourceLabel(p.source_type).toLowerCase() }))
)

const filteredProfiles = computed<ProfileRow[]>(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (q.length === 0) {
    return props.profiles
  }
  return labeledProfiles.value.filter(
    (p) => p.source_info.toLowerCase().includes(q) || p._label.includes(q)
  )
})

const {
  sorted: sortedProfiles,
  sortKey,
  sortDir,
  toggleSort: rawToggleSort,
  sortIndicator
} = useSortedRows<SortKey, ProfileRow>(filteredProfiles, 'timestamp', 'desc')

function toggleSort(key: SortKey) {
  rawToggleSort(key, key === 'timestamp' ? 'desc' : 'asc')
}

function ariaSort(key: SortKey): 'ascending' | 'descending' | 'none' {
  if (sortKey.value !== key) {
    return 'none'
  }
  return sortDir.value === 'asc' ? 'ascending' : 'descending'
}

/* Upload drop zone */
const dragOver = ref(false)
const selectedFile = ref<{ name: string; size: string } | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const uploadFormRef = ref<HTMLFormElement | null>(null)
const uploadFormMissing = ref(false)

function onBrowseClick() {
  fileInputRef.value?.click()
}

function onExternalInputChange() {
  const input = fileInputRef.value
  if (input?.files && input.files.length > 0) {
    const f = input.files[0]!
    selectedFile.value = { name: f.name, size: formatFileSize(f.size) }
  }
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
  dragOver.value = true
}

function onDragLeave() {
  dragOver.value = false
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  dragOver.value = false
  if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
    const input = fileInputRef.value
    if (input) {
      input.files = e.dataTransfer.files
      const f = e.dataTransfer.files[0]!
      selectedFile.value = { name: f.name, size: formatFileSize(f.size) }
    }
  }
}

function clearSelection() {
  selectedFile.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

function submitUpload() {
  uploadFormRef.value?.submit()
}

onMounted(() => {
  // The <form> and <input type="file"> are rendered by the Python side; their
  // ids come through as props to keep the contract explicit. If either is
  // missing, the upload UI is non-functional — surface it both in the
  // console (for developers) and as a visible CmkAlertBox (for admins).
  fileInputRef.value = document.getElementById(props.upload_input_id) as HTMLInputElement | null
  uploadFormRef.value = document.getElementById(props.upload_form_id) as HTMLFormElement | null
  if (fileInputRef.value === null || uploadFormRef.value === null) {
    uploadFormMissing.value = true
    console.error(
      `cmk-profiling-profiles-list: expected #${props.upload_form_id} and #${props.upload_input_id}`
    )
  }
  fileInputRef.value?.addEventListener('change', onExternalInputChange)
})

onUnmounted(() => {
  fileInputRef.value?.removeEventListener('change', onExternalInputChange)
})
</script>

<template>
  <div class="profiling-profiles-list-app">
    <CmkAlertBox v-if="uploadFormMissing" variant="error" :heading="_t('Upload is unavailable')">
      {{
        _t(
          'The upload form was not rendered by the page. Reload the page; if the error persists the performance-profiles feature may be misconfigured.'
        )
      }}
    </CmkAlertBox>
    <CmkAlertBox v-if="props.upload_error" variant="error" :heading="_t('Upload failed')">
      {{ props.upload_error }}
    </CmkAlertBox>
    <!-- Upload: full drop zone when empty, compact bar when profiles exist -->
    <div
      v-if="props.profiles.length === 0"
      class="profiling-profiles-list-app__upload"
      :class="{
        'profiling-profiles-list-app__upload--dragover': dragOver,
        'profiling-profiles-list-app__upload--has-file': selectedFile !== null
      }"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
    >
      <template v-if="selectedFile === null">
        <CmkIcon name="upload" size="xxlarge" class="profiling-profiles-list-app__upload-icon" />
        <div class="profiling-profiles-list-app__upload-text">
          {{ _t('Drag & drop a cProfile dump here') }}
        </div>
        <div class="profiling-profiles-list-app__upload-separator">{{ _t('or') }}</div>
        <CmkButton variant="secondary" @click="onBrowseClick">
          {{ _t('Browse files') }}
        </CmkButton>
        <div class="profiling-profiles-list-app__upload-hint">
          <!-- eslint-disable-next-line vue/no-bare-strings-in-template -- file-size unit -->
          {{ _t('cProfile dumps, max 10 MB') }}
        </div>
      </template>
      <template v-else>
        <div class="profiling-profiles-list-app__upload-file-card">
          <CmkIcon
            name="upload"
            size="xlarge"
            class="profiling-profiles-list-app__upload-file-icon"
          />
          <div class="profiling-profiles-list-app__upload-file-info">
            <div class="profiling-profiles-list-app__upload-file-name">{{ selectedFile.name }}</div>
            <div class="profiling-profiles-list-app__upload-file-size">{{ selectedFile.size }}</div>
          </div>
          <CmkIconButton
            name="close"
            size="small"
            :title="_t('Remove')"
            :aria-label="_t('Remove selected file')"
            @click="clearSelection"
          />
        </div>
        <div class="profiling-profiles-list-app__upload-file-actions">
          <CmkButton variant="primary" @click="submitUpload">
            {{ _t('Upload & analyze') }}
          </CmkButton>
          <CmkButton variant="optional" @click="onBrowseClick">
            {{ _t('Choose different file') }}
          </CmkButton>
        </div>
      </template>
    </div>
    <div
      v-else
      class="profiling-profiles-list-app__upload-compact"
      :class="{ 'profiling-profiles-list-app__upload-compact--dragover': dragOver }"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
    >
      <template v-if="selectedFile === null">
        <CmkIcon
          name="upload"
          size="medium"
          class="profiling-profiles-list-app__upload-compact-icon"
        />
        <span class="profiling-profiles-list-app__upload-compact-text">
          {{ _t('Drop a cProfile dump here or') }}
        </span>
        <CmkButton variant="optional" @click="onBrowseClick">
          {{ _t('Browse') }}
        </CmkButton>
      </template>
      <template v-else>
        <CmkIcon
          name="upload"
          size="medium"
          class="profiling-profiles-list-app__upload-compact-icon"
        />
        <span class="profiling-profiles-list-app__upload-compact-filename">
          {{ selectedFile.name }}
        </span>
        <span class="profiling-profiles-list-app__upload-compact-filesize">
          {{ selectedFile.size }}
        </span>
        <CmkButton variant="primary" @click="submitUpload">
          {{ _t('Upload & analyze') }}
        </CmkButton>
        <CmkIconButton
          name="close"
          size="small"
          :title="_t('Remove')"
          :aria-label="_t('Remove selected file')"
          @click="clearSelection"
        />
      </template>
    </div>

    <div v-if="props.profiles.length > 0" class="profiling-profiles-list-app__toolbar">
      <div class="profiling-profiles-list-app__summary">
        <template v-if="searchQuery">
          {{ filteredProfiles.length }} / {{ props.profiles.length }}
          {{ _t('profiles match') }}
        </template>
        <template v-else> {{ props.profiles.length }} {{ _t('profiles stored') }} </template>
      </div>
      <div class="profiling-profiles-list-app__search-wrap">
        <CmkInput
          v-model="searchValue"
          field-size="medium"
          :placeholder="_t('Search source or type...')"
        />
        <CmkIconButton
          v-if="searchValue"
          name="close"
          size="xsmall"
          :title="_t('Clear search')"
          :aria-label="_t('Clear search')"
          class="profiling-profiles-list-app__search-clear"
          @click="clearSearch"
        />
      </div>
    </div>

    <div v-if="props.profiles.length === 0" class="profiling-profiles-list-app__empty">
      {{
        _t(
          'No profiles stored yet. Enable profiling in Global settings > User interface > Profile requests and perform some requests, run a base command with cmk --profile, or upload a cProfile dump above.'
        )
      }}
    </div>

    <table v-if="filteredProfiles.length > 0" class="profiling-profiles-list-app__table">
      <thead>
        <tr>
          <th
            class="profiling-profiles-list-app__col-timestamp"
            scope="col"
            :aria-sort="ariaSort('timestamp')"
          >
            <button
              type="button"
              class="profiling-profiles-list-app__sort-btn"
              @click="toggleSort('timestamp')"
            >
              {{ _t('Timestamp') }}{{ sortIndicator('timestamp') }}
            </button>
          </th>
          <th
            class="profiling-profiles-list-app__col-type"
            scope="col"
            :aria-sort="ariaSort('source_type')"
          >
            <button
              type="button"
              class="profiling-profiles-list-app__sort-btn"
              @click="toggleSort('source_type')"
            >
              {{ _t('Type') }}{{ sortIndicator('source_type') }}
            </button>
          </th>
          <th
            class="profiling-profiles-list-app__col-source"
            scope="col"
            :aria-sort="ariaSort('source_info')"
          >
            <button
              type="button"
              class="profiling-profiles-list-app__sort-btn"
              @click="toggleSort('source_info')"
            >
              {{ _t('Source') }}{{ sortIndicator('source_info') }}
            </button>
          </th>
          <th
            class="profiling-profiles-list-app__col-duration"
            scope="col"
            :aria-sort="ariaSort('duration_ms')"
          >
            <button
              type="button"
              class="profiling-profiles-list-app__sort-btn"
              @click="toggleSort('duration_ms')"
            >
              {{ _t('Duration') }}{{ sortIndicator('duration_ms') }}
            </button>
          </th>
          <th class="profiling-profiles-list-app__col-actions" scope="col">
            {{ _t('Actions') }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="p in sortedProfiles"
          :key="p.profile_id"
          class="profiling-profiles-list-app__row"
        >
          <td class="profiling-profiles-list-app__col-timestamp">
            {{ formatTimestamp(p.timestamp) }}
          </td>
          <td class="profiling-profiles-list-app__col-type">
            <CmkBadge size="small" color="default" class="profiling-profiles-list-app__type-badge">
              {{ sourceLabel(p.source_type) }}
            </CmkBadge>
          </td>
          <td class="profiling-profiles-list-app__col-source">
            <span class="profiling-profiles-list-app__source-info">{{ p.source_info }}</span>
          </td>
          <td class="profiling-profiles-list-app__col-duration">
            {{ p.duration_ms !== null ? formatMs(p.duration_ms) : '—' }}
          </td>
          <td class="profiling-profiles-list-app__col-actions">
            <CmkIconLink
              name="view"
              size="small"
              :href="p.flamegraph_url"
              :title="_t('View flamegraph')"
              :aria-label="_t('View flamegraph')"
            />
            <CmkIconLink
              name="download"
              size="small"
              :href="p.download_url"
              :title="_t('Download .profile')"
              :aria-label="_t('Download .profile')"
            />
            <CmkIconLink
              name="delete"
              size="small"
              :href="p.delete_url"
              :title="_t('Delete')"
              :aria-label="_t('Delete profile')"
            />
          </td>
        </tr>
      </tbody>
    </table>

    <div
      v-if="props.profiles.length > 0 && filteredProfiles.length === 0"
      class="profiling-profiles-list-app__empty"
    >
      {{ _t('No profiles match the current search.') }}
    </div>
  </div>
</template>

<style scoped>
.profiling-profiles-list-app__upload {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing);

  /* No design-system token for a 2px border width yet — design system has
     --border-width-1 only; treat 2px as an intentional literal until a
     matching token is added. */
  border: 2px dashed var(--ux-theme-6);
  border-radius: var(--border-radius);
  padding: var(--spacing-double) var(--spacing);
  margin-bottom: var(--spacing-double);
  text-align: center;
  transition:
    border-color 0.2s,
    background 0.2s;
}

.profiling-profiles-list-app__upload:hover {
  border-color: var(--ux-theme-8);
}

.profiling-profiles-list-app__upload--dragover {
  border-color: var(--color-dark-blue-50);
  border-style: solid;
  background: var(--ux-theme-3);
}

.profiling-profiles-list-app__upload-icon {
  opacity: 0.4;
}

.profiling-profiles-list-app__upload--dragover .profiling-profiles-list-app__upload-icon {
  opacity: 0.8;
}

.profiling-profiles-list-app__upload-text {
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
}

.profiling-profiles-list-app__upload-separator {
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
  text-transform: uppercase;
}

.profiling-profiles-list-app__upload-hint {
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

/* Selected file state */
.profiling-profiles-list-app__upload--has-file {
  border-style: solid;
  border-color: var(--ux-theme-6);
  padding: var(--spacing);
  gap: var(--spacing);
}

.profiling-profiles-list-app__upload-file-card {
  display: flex;
  align-items: center;
  gap: var(--spacing);
  background: var(--ux-theme-3);
  border-radius: var(--border-radius);
  padding: var(--spacing-half) var(--spacing);
  width: 100%;
  max-width: 400px;
}

.profiling-profiles-list-app__upload-file-icon {
  opacity: 0.5;
  flex-shrink: 0;
}

.profiling-profiles-list-app__upload-file-info {
  flex: 1;
  min-width: 0;
  text-align: left;
}

.profiling-profiles-list-app__upload-file-name {
  font-family: monospace;
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-normal);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profiling-profiles-list-app__upload-file-size {
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.profiling-profiles-list-app__upload-file-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing);
}

/* Compact upload bar (when profiles exist) */
.profiling-profiles-list-app__upload-compact {
  display: flex;
  align-items: center;
  gap: var(--spacing);
  border: var(--border-width-1) dashed var(--ux-theme-6);
  border-radius: var(--border-radius);
  padding: var(--spacing-half) var(--spacing);
  margin-bottom: var(--spacing);
  transition:
    border-color 0.2s,
    background 0.2s;
}

.profiling-profiles-list-app__upload-compact:hover {
  border-color: var(--ux-theme-8);
}

.profiling-profiles-list-app__upload-compact--dragover {
  border-color: var(--color-dark-blue-50);
  border-style: solid;
  background: var(--ux-theme-3);
}

.profiling-profiles-list-app__upload-compact-icon {
  opacity: 0.4;
  flex-shrink: 0;
}

.profiling-profiles-list-app__upload-compact-text {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.profiling-profiles-list-app__upload-compact-filename {
  font-family: monospace;
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-normal);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.profiling-profiles-list-app__upload-compact-filesize {
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
  white-space: nowrap;
}

.profiling-profiles-list-app__empty {
  color: var(--font-color-dimmed);
  font-size: var(--font-size-normal);
  padding: var(--spacing);
}

.profiling-profiles-list-app {
  font-family: inherit;
  color: inherit;
}

.profiling-profiles-list-app__toolbar {
  display: flex;
  align-items: center;
  gap: var(--spacing);
  margin-bottom: var(--spacing);
}

.profiling-profiles-list-app__search-wrap {
  position: relative;
  display: inline-block;
  margin-left: auto;
}

.profiling-profiles-list-app__search-clear {
  position: absolute;
  right: var(--spacing-half);
  top: 50%;
  transform: translateY(-50%);
}

.profiling-profiles-list-app__summary {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.profiling-profiles-list-app__table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-normal);
}

.profiling-profiles-list-app__table th {
  text-align: left;
  padding: var(--spacing-half) var(--spacing);
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
  border-bottom: var(--border-width-1) solid var(--default-form-element-border-color);
  white-space: nowrap;
  user-select: none;
}

.profiling-profiles-list-app__sort-btn {
  all: unset;
  cursor: pointer;
  font: inherit;
  color: inherit;
  transition: color 0.15s;
  white-space: nowrap;
}

.profiling-profiles-list-app__sort-btn:hover,
.profiling-profiles-list-app__sort-btn:focus-visible {
  color: var(--font-color);
}

.profiling-profiles-list-app__sort-btn:focus-visible {
  outline: var(--border-width-1) solid var(--color-dark-blue-50);
  outline-offset: var(--spacing-half);
}

.profiling-profiles-list-app__table td {
  padding: var(--spacing-half) var(--spacing);
  vertical-align: middle;
  border-bottom: var(--border-width-1) solid var(--ux-theme-4);
}

.profiling-profiles-list-app__row {
  transition: background 0.15s;
}

.profiling-profiles-list-app__row:hover {
  background: var(--ux-theme-4);
}

/* Per-column alignment & width. Compound selectors ensure these rules win
   over the base `.profiling-profiles-list-app__table th` rule's left-align. */
.profiling-profiles-list-app__table th.profiling-profiles-list-app__col-timestamp,
.profiling-profiles-list-app__table td.profiling-profiles-list-app__col-timestamp {
  font-family: monospace;
  white-space: nowrap;
}

/* Type column holds just the source_type badge; keep it at its natural width
   so labels like "GUI request" don't wrap. */
.profiling-profiles-list-app__table th.profiling-profiles-list-app__col-type,
.profiling-profiles-list-app__table td.profiling-profiles-list-app__col-type {
  white-space: nowrap;
  width: 1%;
}

.profiling-profiles-list-app__type-badge {
  white-space: nowrap;
}

.profiling-profiles-list-app__table td.profiling-profiles-list-app__col-source {
  max-width: 500px;
}

.profiling-profiles-list-app__source-info {
  font-family: monospace;
  font-size: var(--font-size-normal);
  word-break: break-all;
}

.profiling-profiles-list-app__table th.profiling-profiles-list-app__col-duration,
.profiling-profiles-list-app__table td.profiling-profiles-list-app__col-duration {
  text-align: right;
  font-family: monospace;
  white-space: nowrap;
}

.profiling-profiles-list-app__table th.profiling-profiles-list-app__col-actions,
.profiling-profiles-list-app__table td.profiling-profiles-list-app__col-actions {
  white-space: nowrap;
  text-align: center;
}
</style>
