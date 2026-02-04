<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type ProductUsageAnalyticsConfig } from 'cmk-shared-typing/typescript/product_usage_analytics'
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkPopupDialog from '@/components/CmkPopupDialog.vue'
import CmkSpace from '@/components/CmkSpace.vue'

const { _t } = usei18n()

const props = defineProps<ProductUsageAnalyticsConfig>()

const popupOpen = ref(true)
</script>

<template>
  <CmkPopupDialog
    :open="popupOpen"
    :title="_t('Help us improve Checkmk with product usage analytics')"
    :stay-open-overlay-click="true"
    @close="popupOpen = false"
  >
    <div class="product-usage-analytics-app__content">
      <p>
        <b>{{ _t('We want to understand how you use Checkmk.') }}</b>
        {{
          _t(
            'Product usage analytics allows us to make data-driven decisions and focus development on what parts of Checkmk you regularly use. \
            The data you share will help us prioritize the features that matter most to you.'
          )
        }}
      </p>

      <CmkSpace direction="horizontal" size="small" />

      <h4>{{ _t('What data are we collecting?') }}</h4>
      <ul>
        <li>
          <b>{{ _t('We collect: ') }}</b
          >{{
            _t(
              'data about the general usage of features and configuration options (e.g., counts of hosts, folders, plug-ins, MKPs, and services).'
            )
          }}
        </li>
        <li>
          <b>{{ _t('We do NOT collect: ') }}</b
          >{{
            _t(
              'any data about users or their behavior (e.g., PII) or possibly sensitive identifiers about your environment (e.g., hostnames, file paths, service names).'
            )
          }}
        </li>
      </ul>

      <CmkSpace direction="horizontal" size="small" />

      <p>
        <b>{{ _t('Important: ') }}</b>
        {{
          _t(
            'The names of custom check plug-ins (either developed internally or installed as an MKP from the Checkmk Exchange) will be collected as part of the product usage data. \
            If you use MKPs, we recommend you inspect the data carefully via the data download option to verify the content before opting in, to ensure no sensitive data is included. \
            Do not enable product usage analytics if you do not wish to share this information.'
          )
        }}
      </p>

      <CmkSpace direction="horizontal" size="small" />

      <p>
        <b>{{ _t('Product usage analytics is turned off by default. ') }}</b>
        {{
          _t(
            'We believe in only receiving data you explicitly choose to share. You can enable sharing analytics data any time from global settings. \
            If you do not wish to be reminded, please manage your preferences in global settings.'
          )
        }}
      </p>
    </div>

    <div class="product-usage-analytics-app__buttons">
      <CmkButton variant="secondary" @click="popupOpen = false">{{
        _t('Remind me again in 30 days')
      }}</CmkButton>
      <a
        class="product-usage-analytics-app__link"
        :href="props.global_settings_link"
        target="main"
        @click="popupOpen = false"
        >{{ _t('Manage in global settings') }}</a
      >
    </div>
  </CmkPopupDialog>
</template>

<style scoped>
.product-usage-analytics-app__content {
  padding: var(--dimension-4) var(--dimension-11) var(--dimension-10) var(--dimension-11);
}

.product-usage-analytics-app__buttons {
  display: flex;
  justify-content: flex-end;
  gap: var(--dimension-8);
}

.product-usage-analytics-app__link {
  color: var(--button-primary-text-color);
  background-color: var(--default-button-primary-color);
  border: var(--dimension-1) solid var(--button-primary-border-color);
  padding: 0 var(--dimension-4);
  text-decoration: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--dimension-3);

  &:hover {
    background-color: color-mix(in srgb, var(--default-button-primary-color) 70%, var(--white) 30%);
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
