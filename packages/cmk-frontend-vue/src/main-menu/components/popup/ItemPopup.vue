<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type {
  NavItem,
  NavItemTopic,
  NavItemTopicEntry
} from 'cmk-shared-typing/typescript/main_menu'
import { computed, nextTick, ref } from 'vue'

import DefaultPopup from '@/main-menu/components/popup/DefaultPopup.vue'
import { definedMainMenuItemVueApps } from '@/main-menu/provider/item-vue-apps.ts'
import { getInjectedMainMenu } from '@/main-menu/provider/main-menu'

import ItemTopic from './NavItemTopic.vue'

const mainMenu = getInjectedMainMenu()
const props = defineProps<{
  item: NavItem
  active?: boolean | undefined
}>()

const vueApp = computed(() => {
  if (props.item.vue_app) {
    if (definedMainMenuItemVueApps[props.item.vue_app.id]) {
      return definedMainMenuItemVueApps[props.item.vue_app.id]
    }

    throw new Error(`vue app with id '${props.item.vue_app.id}' not defined `)
  }
  throw new Error('vue app defined within NavItem')
})

const showAllTopic = ref<NavItemTopic | NavItemTopicEntry | null>(null)

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

const FOCUS_RETRY_FRAMES = 120

function focusElementWhenAvailable(elementId: string, framesLeft: number = FOCUS_RETRY_FRAMES) {
  const element = document.getElementById(elementId) as HTMLInputElement | null
  if (element) {
    element.focus()
    return
  }
  if (framesLeft > 0) {
    requestAnimationFrame(() => {
      focusElementWhenAvailable(elementId, framesLeft - 1)
    })
  }
}

mainMenu.onNavigate((item: NavItem) => {
  if (item.id === props.item.id && item.set_focus_on_element_by_id) {
    const elementId = item.set_focus_on_element_by_id
    void nextTick(() => {
      focusElementWhenAvailable(elementId)
    })
  } else {
    showAllTopic.value = null
  }
})
</script>

<template>
  <div :id="`main_menu_${props.item.id}`">
    <template v-if="props.item.vue_app">
      <div
        class="mm-item-popup"
        :class="{
          'mm-item-popup--active': active,
          'mm-item-popup--small': props.item.popup_small
        }"
      >
        <component :is="vueApp" v-bind="props.item.vue_app.data" />
      </div>
    </template>
    <DefaultPopup
      v-else
      class="mm-item-popup"
      :class="{ 'mm-item-popup--active': active, 'mm-item-popup--small': props.item.popup_small }"
      :nav-item-id="props.item.id"
      :header="props.item.header"
      :small="props.item.popup_small"
    >
      <template v-if="props.item.popup_small">
        <div class="mm-item-popup__switch">
          <div
            class="mm-item-popup__show-topic"
            :class="{ 'mm-item-popup__view--hidden': !showAllTopic }"
          >
            <ItemTopic
              v-if="showAllTopic"
              :topic="showAllTopic"
              :nav-item-id="item.id"
              :is-show-all="true"
            />
          </div>
          <div
            class="mm-item-popup__topics mm-item-popup__topics-small"
            :class="{ 'mm-item-popup__view--hidden': !!showAllTopic }"
          >
            <template v-for="topic in item.topics" :key="topic.title">
              <ItemTopic
                v-if="
                  (!topic.is_show_more &&
                    topic.entries.filter((e) => !e.is_show_more).length > 0) ||
                  mainMenu.showMoreIsActive(item.id)
                "
                :topic="topic"
                :nav-item-id="item.id"
                class="mm-item-popup__topics-small"
              />
            </template>
          </div>
        </div>
      </template>
      <template v-else>
        <div v-if="showAllTopic" class="mm-item-popup__show-topic">
          <ItemTopic :topic="showAllTopic" :nav-item-id="item.id" :is-show-all="true" />
        </div>
        <div v-else class="mm-item-popup__topics">
          <template v-for="topic in item.topics" :key="topic.title">
            <ItemTopic
              v-if="
                (!topic.is_show_more && topic.entries.filter((e) => !e.is_show_more).length > 0) ||
                mainMenu.showMoreIsActive(item.id)
              "
              :topic="topic"
              :nav-item-id="item.id"
              :class="{ 'mm-item-popup__topics-small': props.item.popup_small }"
            />
          </template>
        </div>
      </template>
    </DefaultPopup>
  </div>
</template>

<style scoped>
.mm-item-popup__topics {
  display: flex;
  height: calc(100% - 81px);
  flex-wrap: wrap;

  /*
    Workaround for nav item topics overflowing the popup.
    See https://stackoverflow.com/a/68904668
  */
  writing-mode: vertical-lr;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .mm-nav-item-topic {
    writing-mode: horizontal-tb;
  }
}

.mm-item-popup--small {
  .mm-item-popup__topics {
    height: auto;
  }
}

.mm-item-popup__topics-small {
  min-width: 290px;
}

.mm-item-popup__switch {
  display: grid;

  .mm-item-popup__show-topic,
  .mm-item-popup__topics {
    grid-area: 1 / 1;
  }
}

.mm-item-popup__view--hidden {
  visibility: hidden;
  pointer-events: none;
}
</style>
