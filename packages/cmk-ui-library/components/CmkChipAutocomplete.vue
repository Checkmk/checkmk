<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Multi-select over a suggestion source the caller owns: what the user types goes
to `suggest`, what they pick becomes a removable chip.

Navigation follows the same model as a column funnel: the arrow keys move focus
between the suggestion buttons rather than tracking a highlight of their own, so
mounting this inside a funnel gives one continuous list to walk rather than two
competing ones.
-->
<script setup lang="ts">
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue'

const SUGGEST_DEBOUNCE_MS = 200

const KEY_VALUE_SEPARATOR = ':'

const WILDCARD = '*'

const props = defineProps<{
  /** Suggestions for what has been typed so far. A rejection reads as "no matches". */
  suggest: (query: string) => Promise<string[]>
  placeholder?: TranslatedString | undefined
  ariaLabel?: TranslatedString | undefined
  /** Ask `suggest` with an empty query on focus, to seed the list before anything is typed. */
  suggestWhenEmpty?: boolean | undefined
  /**
   * Pick a `key:value` pair in two steps. Picking a suggestion that carries no
   * value yet continues the query as `key:` instead of committing a chip, so
   * `suggest` is asked again — this time for that key's values.
   */
  keyValue?: boolean | undefined
  /**
   * Offer what was typed with a trailing `*` as the first entry, for selecting
   * everything starting with it rather than one named value.
   */
  wildcardOption?: boolean | undefined
  /** Refuse further picks once this many are selected. Unbounded when unset. */
  maxSelected?: number | undefined
}>()

const model = defineModel<string[]>({ default: () => [] })

const { _t } = usei18n()

const query = ref('')
const suggestions = ref<string[]>([])
const isLoading = ref(false)

const field = useTemplateRef<HTMLInputElement>('field')
const list = useTemplateRef<HTMLElement>('list')

let debounceHandle: ReturnType<typeof setTimeout> | undefined
// Only the newest request may write; an earlier one resolving late is discarded.
let latestRequest = 0

const selectedSet = computed(() => new Set(model.value))

const isFull = computed(
  () => props.maxSelected !== undefined && model.value.length >= props.maxSelected
)

// In key:value mode the keys of what came back are offered in their own right,
// so a key can be picked before any of its values is known.
const matchingKeys = computed<string[]>(() => {
  if (!props.keyValue || query.value.includes(KEY_VALUE_SEPARATOR)) {
    return []
  }
  const needle = query.value.trim().toLowerCase()
  const keys = new Set<string>()
  for (const suggestion of suggestions.value) {
    const separator = suggestion.indexOf(KEY_VALUE_SEPARATOR)
    const key = separator > 0 ? suggestion.slice(0, separator) : suggestion
    if (key.toLowerCase().includes(needle)) {
      keys.add(key)
    }
  }
  return [...keys]
})

const wildcardEntry = computed<string[]>(() => {
  const typed = query.value.trim()
  if (!props.wildcardOption || typed === '' || typed.endsWith(WILDCARD)) {
    return []
  }
  return [`${typed}${WILDCARD}`]
})

const openSuggestions = computed<string[]>(() => {
  const seen = new Set<string>()
  const listed: string[] = []
  for (const entry of [...wildcardEntry.value, ...matchingKeys.value, ...suggestions.value]) {
    if (selectedSet.value.has(entry) || seen.has(entry)) {
      continue
    }
    seen.add(entry)
    listed.push(entry)
  }
  return listed
})

const showEmptyHint = computed(
  () => query.value.trim() !== '' && !isLoading.value && openSuggestions.value.length === 0
)

async function runSuggest(text: string): Promise<void> {
  const request = ++latestRequest
  isLoading.value = true
  try {
    const found = await props.suggest(text)
    if (request === latestRequest) {
      suggestions.value = found
    }
  } catch {
    if (request === latestRequest) {
      suggestions.value = []
    }
  } finally {
    if (request === latestRequest) {
      isLoading.value = false
    }
  }
}

function scheduleSuggest(text: string): void {
  clearTimeout(debounceHandle)
  debounceHandle = setTimeout(() => void runSuggest(text), SUGGEST_DEBOUNCE_MS)
}

watch(query, (text) => {
  if (text.trim() === '' && !props.suggestWhenEmpty) {
    clearTimeout(debounceHandle)
    latestRequest++
    suggestions.value = []
    isLoading.value = false
    return
  }
  scheduleSuggest(text)
})

function onFocus(): void {
  if (props.suggestWhenEmpty && suggestions.value.length === 0) {
    void runSuggest(query.value)
  }
}

function completesPair(value: string): boolean {
  if (value.endsWith(WILDCARD)) {
    return true
  }
  const separator = value.indexOf(KEY_VALUE_SEPARATOR)
  return separator > 0 && separator < value.length - 1
}

function select(value: string): void {
  if (isFull.value || selectedSet.value.has(value)) {
    return
  }
  if (props.keyValue && !completesPair(value)) {
    query.value = `${value}${KEY_VALUE_SEPARATOR}`
    field.value?.focus()
    return
  }
  model.value = [...model.value, value]
  query.value = ''
  field.value?.focus()
}

function remove(value: string): void {
  model.value = model.value.filter((selected) => selected !== value)
}

function options(): HTMLElement[] {
  return Array.from(list.value?.querySelectorAll<HTMLElement>('button') ?? [])
}

function moveFocus(delta: number): void {
  const items = options()
  if (items.length === 0) {
    return
  }
  const current = items.indexOf(document.activeElement as HTMLElement)
  if (current < 0) {
    items[delta > 0 ? 0 : items.length - 1]?.focus()
    return
  }
  const next = Math.min(items.length - 1, Math.max(0, current + delta))
  items[next]?.focus()
}

function onArrowDown(): void {
  if (openSuggestions.value.length === 0) {
    return
  }
  void nextTick(() => moveFocus(1))
}

function onArrowUp(): void {
  moveFocus(-1)
}

function onBackspace(): void {
  const last = model.value[model.value.length - 1]
  if (query.value === '' && last !== undefined) {
    remove(last)
  }
}

function onEscape(event: KeyboardEvent): void {
  if (query.value) {
    query.value = ''
    event.stopPropagation()
  }
}

function focus(): void {
  field.value?.focus()
}

defineExpose({ focus })
</script>

<template>
  <div class="cmk-chip-autocomplete">
    <div class="cmk-chip-autocomplete__search">
      <CmkMultitoneIcon
        name="search"
        :primary-color="{ custom: 'var(--color-mist-grey-60)' }"
        size="small"
        aria-hidden="true"
      />
      <input
        ref="field"
        v-model="query"
        type="text"
        class="cmk-chip-autocomplete__field"
        :placeholder="placeholder ?? _t('Search')"
        :aria-label="ariaLabel ?? _t('Search')"
        autocomplete="off"
        @focus="onFocus"
        @keydown.down.prevent="onArrowDown"
        @keydown.up.prevent="onArrowUp"
        @keydown.backspace="onBackspace"
        @keydown.escape="onEscape"
      />
    </div>

    <ul v-if="openSuggestions.length > 0" ref="list" class="cmk-chip-autocomplete__suggestions">
      <li v-for="suggestion in openSuggestions" :key="suggestion">
        <button
          type="button"
          class="cmk-chip-autocomplete__suggestion"
          :disabled="isFull"
          @click="select(suggestion)"
          @keydown.down.prevent="moveFocus(1)"
          @keydown.up.prevent="moveFocus(-1)"
        >
          {{ suggestion }}
        </button>
      </li>
    </ul>

    <p v-else-if="showEmptyHint" class="cmk-chip-autocomplete__hint">
      {{ _t('No matching values') }}
    </p>

    <ul class="cmk-chip-autocomplete__chips">
      <li v-for="value in model" :key="value">
        <CmkChip as-div color="others" variant="outline" size="small">
          {{ value }}
          <template #end>
            <CmkIconButton
              class="cmk-chip-autocomplete__remove"
              name="close"
              size="xsmall"
              :title="_t('Remove %{value}', { value })"
              @click="remove(value)"
            />
          </template>
        </CmkChip>
      </li>
    </ul>

    <p v-if="isFull" class="cmk-chip-autocomplete__hint">
      {{ _t('At most %{count} values can be selected', { count: String(maxSelected) }) }}
    </p>
  </div>
</template>

<style scoped>
.cmk-chip-autocomplete {
  display: flex;
  flex-direction: column;
  min-width: 240px;
}

.cmk-chip-autocomplete__search {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  box-sizing: border-box;
  width: 100%;
  margin: 0 0 var(--dimension-3);
  padding: var(--dimension-2) var(--dimension-4);
  background: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-border-color);
  border-radius: 2px;

  &:focus-within {
    outline: 1px solid var(--success);
    outline-offset: 1px;
  }
}

.cmk-chip-autocomplete__field {
  flex: 1;
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  font: inherit;
  color: var(--font-color);

  &:focus-visible {
    outline: none;
  }
}

.cmk-chip-autocomplete__suggestions,
.cmk-chip-autocomplete__chips {
  list-style: none;
  margin: 0;
  padding: 0;
}

.cmk-chip-autocomplete__suggestions {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid var(--default-form-element-border-color);
  background: var(--default-form-element-bg-color);
}

.cmk-chip-autocomplete__suggestion {
  display: block;
  width: 100%;
  margin: 0;
  padding: var(--dimension-2) var(--dimension-4);
  border: 0;
  background: transparent;
  color: var(--font-color);
  font: inherit;
  text-align: left;
  cursor: pointer;

  &:hover,
  &:focus-visible {
    background: var(--ux-theme-3);
    outline: none;
  }

  &:disabled {
    cursor: default;
    opacity: 0.5;
  }
}

/* Holds its height with no chips in it, so picking the first one does not
   resize the panel it sits in. */
.cmk-chip-autocomplete__chips {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: var(--dimension-3);
  min-height: var(--cmk-chip-autocomplete-chips-min-height, 48px);
  margin-top: var(--dimension-4);
}

.cmk-chip-autocomplete__remove {
  margin-left: var(--dimension-2);
}

.cmk-chip-autocomplete__hint {
  margin: var(--dimension-3) 0 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
