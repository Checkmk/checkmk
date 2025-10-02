<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { NavItemHeader, NavItemIdEnum } from 'cmk-shared-typing/typescript/main_menu'
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import type { CmkMultitoneIconColor, OneColorIcons } from '@/components/CmkIcon/types'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import { getInjectedMainMenu } from '@/main-menu/provider/main-menu'

const { _t } = usei18n()
const mainMenu = getInjectedMainMenu()
const props = defineProps<{
  small?: boolean | undefined
  header?: NavItemHeader | undefined
  navItemId: NavItemIdEnum
}>()

const showMoreHover = ref<boolean>(false)

const showMoreText = computed(() => {
  return mainMenu.showMoreIsActive(props.navItemId) ? _t('show less') : _t('show more')
})
const showMoreColor = computed(() => {
  return (showMoreHover.value ? 'success' : 'font') as CmkMultitoneIconColor
})
const showMoreIcon = computed(() => {
  return (mainMenu.showMoreIsActive(props.navItemId) ? 'show-less' : 'show-more') as OneColorIcons
})

function navigateUrl(url: string) {
  location.href = url
}
</script>

<template>
  <div class="main-menu-popup-menu" :class="{ 'mm-default-popup--small': props.small }">
    <div
      v-if="props.header"
      class="mm-default-popup__header"
      :class="{ 'mm-default-popup--small': props.header }"
    >
      <CmkButton
        v-if="
          props.header.trigger_button && mainMenu.triggerHeader(props.header.trigger_button.mode)
        "
        class="mm-default-popup__header-trigger-button"
        :variant="
          !props.header.trigger_button.color || props.header.trigger_button.color === 'default'
            ? 'optional'
            : props.header.trigger_button.color
        "
        @click="navigateUrl(props.header.trigger_button.url)"
      >
        {{ mainMenu.triggerHeader(props.header.trigger_button.mode) }}
      </CmkButton>
      <div class="mm-default-popup__header-left">
        <CmkHeading v-if="props.header.title" type="h2"></CmkHeading>
        <span v-if="props.header?.info" class="mm-default-popup__header-left-info">
          {{ props.header?.info }}
        </span>
      </div>
      <div v-if="props.header.show_more" class="mm-default-popup__header-show-more">
        <a
          href="javascript:void(0)"
          @mouseenter="
            () => {
              showMoreHover = true
            }
          "
          @mouseleave="
            () => {
              showMoreHover = false
            }
          "
          @click="mainMenu.toggleShowMoreLess(props.navItemId)"
        >
          {{ showMoreText }}
          <CmkMultitoneIcon :name="showMoreIcon" :primary-color="showMoreColor"
        /></a>
      </div>
    </div>

    <slot />
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.main-menu-popup-menu {
  position: absolute;
  top: 58px;
  bottom: 0;
  left: 0;
  min-width: 360px;
  padding-bottom: 20px;
  background-color: var(--ux-theme-1);
  border-right: 4px solid var(--success);

  .mm-default-popup__header {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    height: 60px;
    border-bottom: 1px solid var(--ux-theme-3);
    padding: 0 var(--dimension-5) 0 var(--dimension-8);

    .mm-default-popup__header-trigger-button {
      left: 0;
      position: absolute;
      margin-left: var(--dimension-3);
      height: var(--dimension-7);
      font-weight: var(--font-weight-default);
    }

    .mm-default-popup__header-left {
      display: flex;
      flex-direction: column;
      align-items: flex-start;

      .mm-default-popup__header-left-info {
        color: var(--color-white-50);
      }
    }

    .mm-default-popup__header-show-more {
      a {
        display: flex;
        flex-direction: row;
        align-items: center;
        font-size: var(--font-size-small);
        text-decoration: none;
        gap: var(--dimension-3);

        &:hover {
          color: var(--success);
        }
      }
    }
  }

  &.mm-default-popup--small {
    top: auto;

    .mm-default-popup__header {
      height: 36px;
      justify-content: flex-end;
    }
  }
}
</style>
