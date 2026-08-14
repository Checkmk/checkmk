<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import CmkTabs, { CmkTab, CmkTabContent } from 'cmk-ui-library/components/CmkTabs'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { reactive, ref, watch } from 'vue'

import type { CmkSlideInTabbedProps, SlideInTab, SlideInTabState } from './types'

const { _t } = usei18n()

const props = defineProps<CmkSlideInTabbedProps>()
const emit = defineEmits<{ close: []; 'update:activeTabId': [id: string] }>()

/** Where an opening starts: what a bound `activeTabId` asks for, else the default. */
function initialTab(): string {
  return props.activeTabId ?? props.defaultTabId ?? props.tabs[0]?.id ?? ''
}

const activeTab = ref<string>(initialTab())

// Loaded data is cached per tab so switching back and forth does not re-fetch.
// The cache is cleared whenever the panel is (re)opened, so each opening starts
// from a fresh load of the active tab.
const tabState = reactive<Record<string, SlideInTabState>>({})

function findTab(id: string): SlideInTab | undefined {
  return props.tabs.find((tab) => tab.id === id)
}

async function ensureLoaded(id: string): Promise<void> {
  const tab = findTab(id)
  if (!tab) {
    return
  }
  const existing = tabState[id]
  if (existing && existing.status !== 'error') {
    return
  }
  if (!tab.load) {
    tabState[id] = { status: 'loaded', data: undefined }
    return
  }
  tabState[id] = { status: 'loading' }
  try {
    const data = await tab.load()
    tabState[id] = { status: 'loaded', data }
  } catch (error) {
    tabState[id] = { status: 'error', error }
  }
}

function retry(id: string): void {
  void ensureLoaded(id)
}

function resetTabs(): void {
  for (const key of Object.keys(tabState)) {
    delete tabState[key]
  }
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      resetTabs()
      activeTab.value = initialTab()
      void ensureLoaded(activeTab.value)
    }
  },
  { immediate: true }
)

watch(
  () => props.activeTabId,
  (id) => {
    if (id !== undefined) {
      activeTab.value = id
    }
  }
)

watch(activeTab, (id) => {
  emit('update:activeTabId', id)
  if (props.open) {
    void ensureLoaded(id)
  }
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

      <CmkTabs v-model="activeTab" class="cmk-slide-in-tabbed__tabs">
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
            <component
              :is="tab.skeleton"
              v-if="(!tabState[tab.id] || tabState[tab.id]?.status === 'loading') && tab.skeleton"
            />
            <div
              v-else-if="!tabState[tab.id] || tabState[tab.id]?.status === 'loading'"
              class="cmk-slide-in-tabbed__loading"
            >
              <CmkLoading />
            </div>
            <div
              v-else-if="tabState[tab.id]?.status === 'error'"
              class="cmk-slide-in-tabbed__error"
            >
              <CmkParagraph>
                {{ _t('Could not load this content.') }}
              </CmkParagraph>
              <CmkButton variant="secondary" size="small" @click="retry(tab.id)">
                {{ _t('Retry') }}
              </CmkButton>
            </div>
            <component
              :is="tab.component"
              v-else
              :data="tabState[tab.id]?.data"
              v-bind="tab.props"
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

.cmk-slide-in-tabbed__loading {
  display: flex;
  justify-content: center;
  padding: var(--spacing);
}

.cmk-slide-in-tabbed__error {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--spacing);
}
</style>
