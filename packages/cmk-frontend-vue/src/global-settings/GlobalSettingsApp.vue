<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalSettingsApp } from 'cmk-shared-typing/typescript/global_settings'
import CmkAccordion from 'cmk-ui-library/components/CmkAccordion/CmkAccordion.vue'
import { computed, inject, ref, toRaw } from 'vue'

import { GLOBAL_SETTINGS_SERVICE, globalSettingsService } from './api'
import ExpandCollapseToggle from './components/ExpandCollapseToggle.vue'
import GlobalSettingsEditSlideIn from './components/GlobalSettingsEditSlideIn.vue'
import GlobalSettingsTopic from './components/GlobalSettingsTopic.vue'
import { useGlobalSettingsEditor } from './useGlobalSettingsEditor'

const props = defineProps<GlobalSettingsApp>()

const service = inject(GLOBAL_SETTINGS_SERVICE, globalSettingsService)

const allTopicIds = computed(() => props.topics.map((topic) => topic.headline))
const openedItems = ref<string[]>([])

const editableTopics = ref(structuredClone(toRaw(props.topics)))
const { session, openEditor, closeEditor } = useGlobalSettingsEditor(service, props.scope)
</script>

<template>
  <div class="global-settings-app">
    <div class="global-settings-app__toolbar">
      <ExpandCollapseToggle
        :opened-count="openedItems.length"
        :total-count="allTopicIds.length"
        @expand-all="openedItems = [...allTopicIds]"
        @collapse-all="openedItems = []"
      />
    </div>
    <CmkAccordion v-model="openedItems" :min-open="0" :max-open="0">
      <GlobalSettingsTopic
        v-for="topic in editableTopics"
        :key="topic.headline"
        :topic="topic"
        :value="topic.headline"
        @edit="openEditor"
      />
    </CmkAccordion>
    <GlobalSettingsEditSlideIn
      v-if="session !== null"
      :session="session"
      :title="title"
      @close="closeEditor"
    />
  </div>
</template>

<style scoped>
.global-settings-app {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.global-settings-app__toolbar {
  display: flex;
  justify-content: flex-end;
}
</style>
