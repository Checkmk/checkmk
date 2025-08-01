<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'
import CmkCollapsibleTitle from '@/components/CmkCollapsibleTitle.vue'
import CmkCollapsible from '@/components/CmkCollapsible.vue'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
import CmkZebra from '@/components/CmkZebra.vue'
import usei18n from '@/lib/i18n'
import type { PendingChanges } from '../ChangesInterfaces'

const { t } = usei18n('changes-app')

defineProps<{
  pendingChanges: PendingChanges[]
  selectedSites: string[]
  numberOfForeignChanges: number
  userName: string
}>()

const pendingChangesCollapsible = ref<boolean>(true)
</script>

<template>
  <div class="pending-changes-container">
    <CmkCollapsibleTitle
      :title="`Changes`"
      class="collapsible-title"
      :open="pendingChangesCollapsible"
      @toggle-open="pendingChangesCollapsible = !pendingChangesCollapsible"
    />

    <CmkCollapsible :open="pendingChangesCollapsible" class="cmk-collapsible-pending-changes">
      <CmkIndent class="cmk-indent-foreign-changes-container">
        <div class="cmk-div-foreign-changes-text">
          {{ t('foreign-changes', 'Foreign changes: ') }}
        </div>
        <div class="cmk-div-foreign-changes-text">
          {{ numberOfForeignChanges }}
        </div>
      </CmkIndent>

      <CmkIndent v-if="selectedSites.length === 0" class="cmk-indent-no-sites-selected-container">
        <div class="cmk-div-no-sites-selected">
          {{ t('no-sites-selected', "You haven't selected any sites") }}
        </div>
      </CmkIndent>
      <CmkScrollContainer
        v-if="selectedSites.length > 0"
        class="cmk-scroll-pending-changes-container"
        height="auto"
      >
        <div
          v-for="(change, idx) in pendingChanges"
          :key="change.changeId"
          class="cmk-div-pending-changes-container"
        >
          <CmkZebra :num="idx">
            <CmkIndent
              v-if="
                change.whichSites.includes('All sites') ||
                change.whichSites.some((site) => selectedSites.includes(site))
              "
              class="cmk-indent-pending-change-container"
              :class="{ 'red-text': change.user !== userName && change.user !== null }"
            >
              <span class="cmk-span-pending-change-text">{{ change.changeText }}</span>

              <div
                class="cmk-div-pending-change-details"
                :class="{ 'grey-text': change.user === userName || change.user === null }"
              >
                <div class="cmk-div-user-sites-timestamp">
                  <span>{{ change.user }}</span>
                  <span>|</span>
                  <span>{{ change.whichSites.join(', ') }}</span>
                </div>
                <span>{{ change.timestring }}</span>
              </div>
            </CmkIndent>
          </CmkZebra>
        </div>
      </CmkScrollContainer>
    </CmkCollapsible>
  </div>
</template>

<style scoped>
.pending-changes-container {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.collapsible-title {
  position: relative;
  height: auto;
  padding: 4px 10px 3px 9px;
  margin-top: 16px;

  font-weight: bold;
  letter-spacing: 1px;
  background-color: var(--ux-theme-5);
  width: 100%;
  box-sizing: border-box;
  display: block;
  text-align: left;
}

.cmk-collapsible-pending-changes {
  width: 100%;
  height: calc(100% - 158px);
}

:deep(.cmk-collapsible__content) {
  height: 100%;
}

.cmk-indent-foreign-changes-container {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 6px;
  border-bottom: 2px solid var(--ux-theme-4) !important;
}

.cmk-indent-no-sites-selected-container {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.cmk-div-no-sites-selected {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: var(--font-color-dimmed);
  font-size: 12px;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
  letter-spacing: 0.36px;
  margin-top: 15px;
  margin-bottom: 15px;
}

.cmk-scroll-pending-changes-container {
  width: inherit;
  display: flex;
  flex-direction: column;
}

.cmk-div-pending-changes-container {
  display: flex;
  width: 100%;
  padding: 0px;
  flex-direction: column;
  align-items: flex-start;
}

.cmk-indent-pending-change-container {
  display: flex;
  width: 100%;
  padding: 8px !important;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  box-sizing: border-box;
}

.red-text {
  color: var(--color-danger);
}

.cmk-span-pending-change-text {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  align-self: stretch;
  color: var(--font-color);
  font-size: 12px;
  font-style: normal;
  font-weight: 700;
  line-height: normal;
  letter-spacing: 0.36px;
}

.cmk-div-pending-change-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
  align-self: stretch;
  color: var(--font-color-dimmed);
  font-size: 12px;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
  letter-spacing: 0.36px;
}

.grey-text {
  color: var(--font-color-dimmed);
}

.cmk-div-user-sites-timestamp {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
