<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, onBeforeUnmount, onMounted, ref, useTemplateRef } from 'vue'

const props = defineProps<{
  modelValue: string
  placeholder?: TranslatedString
  excludePrefixes?: readonly string[]
  // Embed in a normal toolbar flow instead of floating fixed top-right (used by
  // maps whose canvas fills 100%, e.g. the folder treemap, where a floating
  // overlay would cover data).
  inline?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [string] }>()

const { _t } = usei18n()

const operators = computed(() => {
  const all = [
    { prefix: 'h', label: _t('Host') },
    { prefix: 's', label: _t('Service') },
    { prefix: 'hg', label: _t('Host group') },
    { prefix: 'sg', label: _t('Service group') },
    { prefix: 'id', label: _t('Object ID') }
  ]
  return all.filter((op) => !props.excludePrefixes?.includes(op.prefix))
})

const local = computed({
  get: () => props.modelValue,
  set: (v: string) => emit('update:modelValue', v)
})

const rootRef = useTemplateRef<HTMLElement>('rootRef')
const inputRef = useTemplateRef<HTMLInputElement>('inputRef')
const dropdownOpen = ref(false)

function openDropdown() {
  dropdownOpen.value = true
}
function closeDropdown() {
  dropdownOpen.value = false
}
function toggleDropdown() {
  if (dropdownOpen.value) {
    closeDropdown()
  } else {
    openDropdown()
  }
  if (dropdownOpen.value) {
    inputRef.value?.focus()
  }
}
function syncDropdownFromInput() {
  // Read the live DOM value, not local/modelValue: on @input the v-model
  // emit hasn't propagated back through the prop yet, so local still holds
  // the previous keystroke and the "/" dropdown would open one char late.
  if (inputRef.value?.value.trim().startsWith('/')) {
    openDropdown()
  }
}

function clearAll() {
  local.value = ''
  closeDropdown()
  inputRef.value?.focus()
}

function applyOperator(prefix: string) {
  const current = local.value
  const trimmed = current.trimStart()
  const leadingWs = current.slice(0, current.length - trimmed.length)
  if (trimmed.startsWith('/')) {
    const rest = trimmed.slice(1).trimStart()
    local.value = `${leadingWs + prefix}:${rest}`
  } else if (trimmed.length === 0) {
    local.value = `${prefix}:`
  } else {
    local.value = `${current.replace(/\s+$/, '')} ${prefix}:`
  }
  closeDropdown()
  inputRef.value?.focus()
}

function onDocumentClick(event: MouseEvent) {
  if (!dropdownOpen.value) {
    return
  }
  if (!rootRef.value) {
    return
  }
  if (!rootRef.value.contains(event.target as Node)) {
    closeDropdown()
  }
}

onMounted(() => document.addEventListener('mousedown', onDocumentClick))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocumentClick))
</script>

<template>
  <div
    ref="rootRef"
    class="maps-map-search"
    :class="{ 'maps-map-search--open': dropdownOpen, 'maps-map-search--inline': inline }"
  >
    <svg
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="2"
      class="maps-map-search__search-icon"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 105.62 5.62a7.5 7.5 0 0011.03 11.03z"
      />
    </svg>
    <input
      ref="inputRef"
      v-model="local"
      :placeholder="placeholder ?? _t('Search — type \'/\' for operators')"
      type="search"
      class="maps-map-search__input"
      :aria-label="placeholder ?? _t('Search — type \'/\' for operators')"
      @focus="syncDropdownFromInput"
      @input="syncDropdownFromInput"
      @keydown.escape.stop="closeDropdown"
    />
    <button
      v-if="local"
      type="button"
      class="maps-map-search__icon-btn"
      :title="_t('Clear search')"
      :aria-label="_t('Clear search')"
      @click="clearAll"
    >
      {{ untranslated('×') }}
    </button>
    <button
      type="button"
      class="maps-map-search__icon-btn maps-map-search__help"
      :class="{ 'maps-map-search__help--active': dropdownOpen }"
      :title="_t('Show search operators')"
      :aria-label="_t('Show search operators')"
      :aria-expanded="dropdownOpen"
      @click="toggleDropdown"
    >
      ?
    </button>
    <slot name="trailing" />

    <div v-if="dropdownOpen" class="maps-map-search__dropdown" role="listbox" @mousedown.prevent>
      <div class="maps-map-search__dropdown-title">
        {{ _t("Type '/' to use a search operator") }}
      </div>
      <ul class="maps-map-search__operator-list">
        <li
          v-for="op in operators"
          :key="op.prefix"
          role="option"
          class="maps-map-search__operator"
          @click="applyOperator(op.prefix)"
        >
          <span class="maps-map-search__operator-tag">{{ op.prefix }}:</span>
          <span class="maps-map-search__operator-label">{{ op.label }}</span>
        </li>
      </ul>
      <div class="maps-map-search__info">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          class="maps-map-search__info-icon"
        >
          <circle cx="12" cy="12" r="9" />
          <line x1="12" y1="11" x2="12" y2="16" />
          <circle cx="12" cy="8" r="0.5" fill="currentColor" />
        </svg>
        <span>{{
          _t('Without a prefix all fields are searched. Multiple terms are AND-combined.')
        }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.maps-map-search {
  position: fixed;
  top: calc(36px + var(--dimension-5));
  right: var(--dimension-5);
  z-index: 6;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: var(--border-radius);
  background: var(--maps-map-view-glass);
  border: 1px solid var(--default-border-color);
  backdrop-filter: blur(6px);
  min-width: 300px;
}

/* Embedded in a toolbar: sit in the normal flow, no float/glass, so it never
   covers map content. */
.maps-map-search--inline {
  position: relative;
  top: auto;
  right: auto;
  z-index: auto;
  min-width: 0;
  width: 260px;
  backdrop-filter: none;
  background: var(--ux-theme-1);
}

.maps-map-search__search-icon {
  flex-shrink: 0;
  width: 12px;
  height: 12px;
  color: var(--font-color-dimmed);
}

.maps-map-search__input {
  flex: 1;
  min-width: 0;
  background: transparent;
  border: none;
  outline: none;
  color: var(--font-color);
  font-size: var(--font-size-normal);
}

.maps-map-search__input::placeholder {
  color: var(--font-color-dimmed);
}

/* We render our own clear button — hide the native one to avoid a duplicate "×". */
.maps-map-search__input::-webkit-search-cancel-button {
  display: none;
}

.maps-map-search__icon-btn {
  background: transparent;
  border: none;
  color: var(--font-color-dimmed);
  cursor: pointer;
  font-size: var(--font-size-large);
  line-height: 1;
  padding: 0 4px;
  border-radius: 3px;
}

.maps-map-search__icon-btn:hover {
  color: var(--font-color);
  background: rgb(255 255 255 / 8%);
}

.maps-map-search__help {
  font-weight: var(--font-weight-bold);
  font-size: 11px;
}

.maps-map-search__help--active {
  color: var(--font-color);
  background: rgb(255 255 255 / 10%);
}

.maps-map-search__dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  z-index: 20;
  background: var(--ux-theme-1, rgb(24 24 27 / 98%));
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  box-shadow: 0 8px 24px rgb(0 0 0 / 35%);
  overflow: hidden;
}

.maps-map-search__dropdown-title {
  padding: 6px 10px;
  font-size: 11px;
  font-weight: var(--font-weight-bold);
  color: var(--font-color-dimmed);
  border-bottom: 1px solid var(--default-border-color);
}

.maps-map-search__operator-list {
  list-style: none;
  margin: 0;
  padding: 4px 0;
  max-height: 320px;
  overflow-y: auto;
}

.maps-map-search__operator {
  display: flex;
  align-items: center;
  gap: var(--spacing);
  padding: 6px 10px;
  cursor: pointer;
  font-size: var(--font-size-normal);
  color: var(--font-color);
}

.maps-map-search__operator:hover {
  background: rgb(255 255 255 / 6%);
}

.maps-map-search__operator-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  padding: 1px 6px;
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  font-family: var(--font-monospace, ui-monospace, monospace);
  font-size: 11px;
  color: var(--font-color);
  background: rgb(255 255 255 / 4%);
}

.maps-map-search__operator-label {
  color: var(--font-color);
}

.maps-map-search__info {
  display: flex;
  align-items: flex-start;
  gap: var(--dimension-4);
  padding: 8px 10px;
  border-top: 1px solid var(--default-border-color);
  background: rgb(255 255 255 / 3%);
  font-size: 11px;
  line-height: 1.4;
  color: var(--font-color-dimmed);
}

.maps-map-search__info-icon {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  color: var(--color-accent, #6ea8fe);
  margin-top: var(--dimension-1);
}
</style>
