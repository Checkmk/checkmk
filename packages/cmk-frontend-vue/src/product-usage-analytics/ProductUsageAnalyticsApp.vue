<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type I18N } from 'cmk-shared-typing/typescript/product_usage_analytics'
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton.vue'
import CmkPopupDialog from '@/components/CmkPopupDialog.vue'
import CmkSpace from '@/components/CmkSpace.vue'

const props = defineProps<{
  global_settings_link: string
  i18n: I18N
}>()

const popupOpen = ref(true)
</script>

<template>
  <CmkPopupDialog
    :open="popupOpen"
    :title="props.i18n.popup_title"
    :stay-open-overlay-click="true"
    @close="popupOpen = false"
  >
    <div class="product-usage-analytics-app__content">
      <p>
        <b>{{ props.i18n.why_need_title }}</b>
        {{ props.i18n.why_need_description }}
      </p>

      <CmkSpace direction="horizontal" size="small" />

      <h4>{{ props.i18n.what_collect_title }}</h4>
      <ul>
        <li>
          <b>{{ props.i18n.we_collect_label }}</b
          >{{ props.i18n.we_collect_details }}
        </li>
        <li>
          <b>{{ props.i18n.we_do_not_collect_label }}</b
          >{{ props.i18n.we_do_not_collect_details }}
        </li>
      </ul>

      <CmkSpace direction="horizontal" size="small" />

      <p>
        <b>{{ props.i18n.mkp_warning_title }}</b>
        {{ props.i18n.mkp_warning_description }}
      </p>

      <CmkSpace direction="horizontal" size="small" />

      <p>
        <b>{{ props.i18n.global_settings_hint_title }}</b>
        {{ props.i18n.global_settings_hint_description }}
      </p>
    </div>

    <div class="product-usage-analytics-app__buttons">
      <CmkButton variant="secondary" @click="popupOpen = false">{{
        props.i18n.ask_later_button
      }}</CmkButton>
      <a
        class="product-usage-analytics-app__link"
        :href="props.global_settings_link"
        target="main"
        @click="popupOpen = false"
        >{{ props.i18n.enable_settings_button }}</a
      >
    </div>
  </CmkPopupDialog>
</template>

<style scoped>
.product-usage-analytics-app__content {
  padding: 8px 36px 32px 36px;
}

.product-usage-analytics-app__buttons {
  display: flex;
  justify-content: flex-end;
  gap: 24px;
}

.product-usage-analytics-app__link {
  color: #212121;
  background-color: var(--form-element-required-color);
  border: 1px solid var(--default-submit-button-border-color);
  padding: 0 8px;
  text-decoration: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;

  &:visited {
    color: #212121;
  }

  &:hover {
    background-color: color-mix(in srgb, var(--default-select-hover-color) 70%, var(--white) 30%);
  }

  &:active {
    background-color: color-mix(
      in srgb,
      var(--default-button-primary-color) 90%,
      var(--color-conference-grey-10) 10%
    );
  }
}
</style>
