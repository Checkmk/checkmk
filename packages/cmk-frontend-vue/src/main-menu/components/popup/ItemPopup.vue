<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { NavItem, NavItemTopic } from 'cmk-shared-typing/typescript/main_menu'
import { computed, onMounted, ref } from 'vue'

import DefaultPopup from '../../components/popup/DefaultPopup.vue'
import { definedMainMenuItemVueApps } from '../../provider/item-vue-apps.ts'
import { getInjectedMainMenu } from '../../provider/main-menu'
import ItemTopic from './NavItemTopic.vue'

const mainMenu = getInjectedMainMenu()
const props = defineProps<{ item: NavItem; active?: boolean | undefined }>()

const vueApp = computed(() => {
  if (props.item.vue_app) {
    if (definedMainMenuItemVueApps[props.item.vue_app.id]) {
      return definedMainMenuItemVueApps[props.item.vue_app.id]
    }

    throw new Error(`vue app with id '${props.item.vue_app.id}' not defined `)
  }
  throw new Error('vue app defined within NavItem')
})

const showAllTopic = ref<NavItemTopic | null>(null)

mainMenu.onShowAllEntriesOfTopic((id, topic) => {
  if (id === props.item.id) {
    showAllTopic.value = topic
  }
})

mainMenu.onCloseShowAllEntriesOfTopic((id) => {
  if (id === props.item.id) {
    showAllTopic.value = null
  }
})

onMounted(() => {
  if (props.item.set_focus_on_element_by_id) {
    document.getElementById(props.item.set_focus_on_element_by_id)?.focus()
  }
})
</script>

<template>
  <div>
    <template v-if="props.item.vue_app"
      ><component :is="vueApp" v-bind="props.item.vue_app.data"
    /></template>
    <DefaultPopup
      v-else
      class="mm-item-popup"
      :class="{ 'mm-item-popup--active': active }"
      :nav-item-id="props.item.id"
      :header="props.item.header"
      :small="props.item.popup_small"
    >
      <div v-if="showAllTopic" class="mm-item-popup__show-topic">
        <ItemTopic :topic="showAllTopic" :nav-item-id="item.id" :is-show-all="true" />
      </div>
      <div v-else class="mm-item-popup__topics">
        <template v-for="topic in item.topics" :key="topic.title">
          <ItemTopic
            v-if="!topic.show_more_mode || mainMenu.showMoreIsActive(item.id)"
            :topic="topic"
            :nav-item-id="item.id"
          />
        </template>
      </div>
    </DefaultPopup>
  </div>
</template>

<style scoped>
.mm-item-popup--active {
  display: flex;
}

.mm-item-popup__topics {
  display: flex;
  flex-flow: column wrap;
  height: calc(100% - 81px);
}
</style>
