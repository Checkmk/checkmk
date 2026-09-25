<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The popup a floating edit button opens: a short list of choices above the
button, with the active one ticked. Used by the add-object picker and the
grid-size menu, which differ only in what they list.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { onMounted, ref, useTemplateRef } from 'vue'

/** How far each navigation key moves through the entries. */
const STEP: Record<string, number> = { ArrowDown: 1, ArrowUp: -1 }

export interface MapEditMenuEntry {
  /** Identifies the entry to the caller; not shown. */
  key: string
  title: TranslatedString
  active?: boolean
}

const props = defineProps<{
  label: TranslatedString
  entries: MapEditMenuEntry[]
  /** 'radio' when the entries are alternatives and one of them is in effect. */
  choice?: boolean
}>()

defineEmits<{ pick: [key: string] }>()

const items = useTemplateRef<HTMLButtonElement[]>('items')

// A menu is one stop in the tab order, walked with the arrow keys from there:
// only the entry the operator is on is tabbable, the rest are reachable but
// skipped. Opening starts on the one already in effect, so a grid size can be
// changed without counting down the list.
const focused = ref(
  Math.max(
    0,
    props.entries.findIndex((entry) => entry.active)
  )
)

function focusAt(index: number): void {
  const count = props.entries.length
  if (count === 0) {
    return
  }
  focused.value = (index + count) % count
  items.value?.[focused.value]?.focus()
}

onMounted(() => focusAt(focused.value))

function onKeydown(event: KeyboardEvent, index: number): void {
  const step = STEP[event.key]
  if (step !== undefined) {
    event.preventDefault()
    focusAt(index + step)
  } else if (event.key === 'Home') {
    event.preventDefault()
    focusAt(0)
  } else if (event.key === 'End') {
    event.preventDefault()
    focusAt(props.entries.length - 1)
  }
}
</script>

<template>
  <div class="maps-map-edit-menu" role="menu" :aria-label="label">
    <button
      v-for="(entry, index) in entries"
      :key="entry.key"
      ref="items"
      type="button"
      :role="choice ? 'menuitemradio' : 'menuitem'"
      :aria-checked="choice ? !!entry.active : undefined"
      :tabindex="index === focused ? 0 : -1"
      class="maps-map-edit-menu__item"
      @click="$emit('pick', entry.key)"
      @focus="focused = index"
      @keydown="onKeydown($event, index)"
    >
      <CmkIcon
        :name="choice ? 'checkmark' : 'add'"
        size="small"
        class="maps-map-edit-menu__icon"
        :class="{ 'maps-map-edit-menu__icon--hidden': choice && !entry.active }"
      />
      <span>{{ entry.title }}</span>
    </button>
  </div>
</template>

<style scoped>
.maps-map-edit-menu {
  position: absolute;
  right: 0;
  bottom: 100%;
  width: 224px;
  margin-bottom: var(--dimension-4);
  overflow: hidden;
  background: var(--ux-theme-3);
  border-radius: var(--dimension-5);
  box-shadow:
    0 0 0 1px var(--default-border-color),
    0 25px 50px -12px rgb(0 0 0 / 60%);
}

/* The entries are buttons, which Checkmk styles page-wide: the reset keeps
   them plain rows. */
.maps-map-edit-menu__item {
  display: flex;
  align-items: center;
  gap: var(--spacing);
  box-sizing: border-box;
  width: 100%;
  margin: 0;
  padding: var(--dimension-4) var(--dimension-5);
  font-size: var(--font-size-normal);
  font-weight: inherit;
  letter-spacing: inherit;
  color: var(--font-color);
  text-align: left;
  background: none;
  border: none;
  border-radius: 0;
  cursor: pointer;
}

.maps-map-edit-menu__item:hover {
  background: var(--input-hover-bg-color);
}

.maps-map-edit-menu__icon {
  flex-shrink: 0;
}

.maps-map-edit-menu__icon--hidden {
  visibility: hidden;
}
</style>
