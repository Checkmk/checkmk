<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Multi-site picker for foldertree map settings: a CmkDropdown adds one site at a
time, selected sites show as removable chips. Built on CmkDropdown rather than
vendoring CMK's (stubbed) multi-choice form.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

const props = defineProps<{
  modelValue: string[]
  options: { id: string; alias: string }[]
}>()
const emit = defineEmits<{ 'update:modelValue': [string[]] }>()

const { _t } = usei18n()

const aliasOf = (id: string) => props.options.find((o) => o.id === id)?.alias ?? id

// Only sites not already picked are offered; an empty list collapses the
// dropdown to its "no elements" state.
const available = computed(() => ({
  type: 'filtered' as const,
  suggestions: props.options
    .filter((o) => !props.modelValue.includes(o.id))
    .map((o) => ({ name: o.id, title: untranslated(o.alias) }))
}))

function add(id: string | null) {
  if (id && !props.modelValue.includes(id)) {
    emit('update:modelValue', [...props.modelValue, id])
  }
}
function remove(id: string) {
  emit(
    'update:modelValue',
    props.modelValue.filter((s) => s !== id)
  )
}
</script>

<template>
  <div class="maps-folder-tree-sites-select">
    <div v-if="modelValue.length" class="maps-folder-tree-sites-select__chips">
      <span v-for="id in modelValue" :key="id" class="maps-folder-tree-sites-select__chip">
        {{ aliasOf(id) }}
        <button
          type="button"
          class="maps-folder-tree-sites-select__remove"
          :aria-label="_t('Remove %{site}', { site: aliasOf(id) })"
          @click="remove(id)"
        >
          {{ untranslated('×') }}
        </button>
      </span>
    </div>
    <CmkDropdown
      :model-value="null"
      :options="available"
      width="fill"
      :label="_t('Sites')"
      :input-hint="_t('Add site…')"
      @update:model-value="add"
    />
  </div>
</template>

<style scoped>
.maps-folder-tree-sites-select {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.maps-folder-tree-sites-select__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-2);
}

.maps-folder-tree-sites-select__chip {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
  padding: 2px var(--dimension-3);
  border-radius: var(--border-radius-half);
  background: var(--input-hover-bg-color);
  border: 1px solid var(--default-border-color);
  font-size: var(--font-size-small, 11.375px);
  color: var(--font-color);
}

.maps-folder-tree-sites-select__remove {
  border: 0;
  background: transparent;
  color: var(--font-color-dimmed);
  cursor: pointer;
  font-size: var(--font-size-large);
  line-height: 1;
  padding: 0;
}

.maps-folder-tree-sites-select__remove:hover {
  color: var(--font-color);
}
</style>
