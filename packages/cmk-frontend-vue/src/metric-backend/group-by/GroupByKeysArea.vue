<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import type { QuerySuggestionsFn } from 'cmk-ui-library/components/CmkSuggestions/types'
import usei18n from 'cmk-ui-library/lib/i18n'
import { randomId } from 'cmk-ui-library/lib/randomId'
import { ref } from 'vue'

import GroupByKeyPill from './GroupByKeyPill.vue'
import { isKeyValid } from './types'
import type { AttributeKind, GroupKey } from './types'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    querySuggestions: QuerySuggestionsFn
    suggestionRevision?: number
    resolveAttributeKind?: ((key: string) => AttributeKind | null) | undefined
    canAdd?: boolean
    hideAttributeKind?: boolean
    testid?: string | undefined
  }>(),
  { suggestionRevision: 0, canAdd: true, hideAttributeKind: false }
)

const keys = defineModel<GroupKey[]>({ required: true })

const editingId = ref<string | null>(null)

const pillRefs = new Map<string, InstanceType<typeof GroupByKeyPill>>()

function registerPill(id: string, element: unknown): void {
  if (element) {
    pillRefs.set(id, element as InstanceType<typeof GroupByKeyPill>)
  } else {
    pillRefs.delete(id)
  }
}

function tryChangeFocus(): boolean {
  const id = editingId.value
  if (id === null) {
    return true
  }
  const key = keys.value.find((candidate) => candidate.id === id)
  if (!key || isKeyValid(key)) {
    return true
  }
  pillRefs.get(id)?.revealValidationErrors()
  return false
}

function focusKey(id: string): void {
  editingId.value = id
}

function addKey(): void {
  if (!tryChangeFocus()) {
    return
  }
  const fresh: GroupKey = { id: randomId(), attributeKind: null, attributeKey: '' }
  keys.value = [...keys.value, fresh]
  editingId.value = fresh.id
}

function removeKey(target: GroupKey): void {
  if (editingId.value === target.id) {
    editingId.value = null
  }
  keys.value = keys.value.filter((key) => key.id !== target.id)
}

function mapKeys(transform: (key: GroupKey) => GroupKey): void {
  keys.value = keys.value.map(transform)
}

function updateAttributeKind(target: GroupKey, value: AttributeKind): void {
  mapKeys((key) => (key.id === target.id ? { ...key, attributeKind: value } : key))
}

// Override the kind only when the key resolves, so a user-picked kind survives free-text edits.
function updateAttributeKey(target: GroupKey, value: string): void {
  const inferred = value !== '' ? (props.resolveAttributeKind?.(value) ?? null) : null
  mapKeys((key) =>
    key.id === target.id
      ? { ...key, attributeKey: value, ...(inferred !== null ? { attributeKind: inferred } : {}) }
      : key
  )
}

function startEditing(id: string): void {
  if (!tryChangeFocus()) {
    return
  }
  editingId.value = id
}

function onKeyEditDone(id: string): void {
  if (editingId.value === id) {
    editingId.value = null
  }
}

defineExpose({ tryChangeFocus, focusKey })
</script>

<template>
  <div class="metric-backend-group-by-keys-area" :data-testid="testid">
    <span v-if="keys.length === 0" class="metric-backend-group-by-keys-area__everything">{{
      _t('everything')
    }}</span>
    <GroupByKeyPill
      v-for="key in keys"
      :key="key.id"
      :ref="(element) => registerPill(key.id, element)"
      :condition="key"
      :query-suggestions="querySuggestions"
      :suggestion-revision="suggestionRevision"
      :hide-attribute-kind="hideAttributeKind"
      removable
      :editing="key.id === editingId"
      @remove="removeKey(key)"
      @edit="startEditing(key.id)"
      @done="onKeyEditDone(key.id)"
      @update:attribute-kind="(value) => updateAttributeKind(key, value)"
      @update:attribute-key="(value) => updateAttributeKey(key, value)"
    />
    <CmkIconButton
      v-if="canAdd"
      class="metric-backend-group-by-keys-area__add"
      name="add"
      size="large"
      :title="_t('Add group key')"
      :aria-label="_t('Add group key')"
      @mousedown.prevent
      @click="addKey"
    />
  </div>
</template>

<style scoped>
.metric-backend-group-by-keys-area {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-3) var(--dimension-4);
}

.metric-backend-group-by-keys-area__everything {
  color: var(--font-color-dimmed);
  font-style: italic;
}

.metric-backend-group-by-keys-area__add:hover {
  background-color: var(--input-hover-bg-color);
}
</style>
