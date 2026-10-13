<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAsyncContent from 'cmk-ui-library/components/CmkAsyncContent'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import CmkTabs, { CmkTab, CmkTabContent } from 'cmk-ui-library/components/CmkTabs'
import { ref, watch } from 'vue'

import type { CmkSlideInTabbedProps } from './types'

const props = defineProps<CmkSlideInTabbedProps>()
const emit = defineEmits<{ close: []; 'update:activeTabId': [id: string] }>()

/** Where an opening starts when nothing is bound: the named default, else the first tab. */
function fallbackTab(): string {
  return props.defaultTabId ?? props.tabs[0]?.id ?? ''
}

/** Where an opening starts: what a bound `activeTabId` asks for, else the fallback. */
function initialTab(): string {
  return props.activeTabId ?? fallbackTab()
}

const activeTab = ref<string>(initialTab())

// Which bodies exist. A tab is built the first time it is asked for, and kept
// once built, so switching back and forth does not load it again; the panel
// itself is torn down when it closes, which is what makes each opening fresh.
const visited = ref(new Set<string>([activeTab.value]))

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      activeTab.value = initialTab()
      visited.value = new Set([activeTab.value])
    }
  },
  { immediate: true }
)

watch(
  () => props.activeTabId,
  (id) => {
    activeTab.value = id ?? fallbackTab()
  }
)

// Same effect as reopening the panel (the `open` watcher above), but triggered by the
// consuming page - e.g. once an action it ran may have changed what the open tabs show.
watch(
  () => props.reloadToken,
  (token) => {
    if (token === undefined) {
      return
    }
    visited.value = new Set([activeTab.value])
  }
)

watch(activeTab, (id) => {
  emit('update:activeTabId', id)
  visited.value = new Set(visited.value).add(id)
})
</script>

<template>
  <CmkSlideInDialog
    :open="open"
    :size="size"
    :border-color="borderColor"
    v-bind="header ? { header } : {}"
    @close="emit('close')"
  >
    <div class="cmk-slide-in-tabbed__above-tabs">
      <slot name="above-tabs" />
    </div>

    <div v-if="overrideActive" class="cmk-slide-in-tabbed__override">
      <slot name="override" />
    </div>

    <template v-else>
      <div v-if="$slots.actions" class="cmk-slide-in-tabbed__actions">
        <slot name="actions" />
      </div>

      <!-- Hidden tabs keep their bodies, so what a body loaded survives a trip
           to another tab; `visited` is what keeps the unasked-for ones unbuilt. -->
      <CmkTabs v-model="activeTab" :unmount-on-hide="false" class="cmk-slide-in-tabbed__tabs">
        <template #tabs>
          <CmkTab
            v-for="tab in tabs"
            :id="tab.id"
            :key="tab.id"
            :variant="tab.variant"
            :disabled="tab.disabled"
          >
            {{ tab.title }}
          </CmkTab>
        </template>
        <template #tab-contents>
          <CmkTabContent v-for="tab in tabs" :id="tab.id" :key="tab.id">
            <!-- Keyed by the token so the tab on screen, which the reset above leaves
                 mounted, is built anew and loads again like the dropped ones. -->
            <CmkAsyncContent
              v-if="visited.has(tab.id)"
              :key="`${tab.id}-${reloadToken ?? 0}`"
              v-bind="tab"
            />
          </CmkTabContent>
        </template>
      </CmkTabs>
    </template>
  </CmkSlideInDialog>
</template>

<style scoped>
.cmk-slide-in-tabbed__above-tabs {
  margin: var(--spacing-double) 0;
}

.cmk-slide-in-tabbed__actions {
  margin: var(--spacing-double) 0;
}

.cmk-slide-in-tabbed__above-tabs:empty {
  display: none;
}
</style>
