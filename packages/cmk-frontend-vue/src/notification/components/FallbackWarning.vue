<script setup lang="ts">
import type { FallbackWarning } from '@/form/components/vue_formspec_components'
import Button from '@/quick-setup/components/IconButton.vue'

const props = defineProps<{
  properties: FallbackWarning
}>()

import { ref, onMounted } from 'vue'

const isContentVisible = ref(true)

function hideContent() {
  isContentVisible.value = false
  localStorage.setItem(`${props.properties.user_id}-notificationFallbackVisibility`, 'hidden')
}

onMounted(() => {
  const savedState = localStorage.getItem(
    `${props.properties.user_id}-notificationFallbackVisibility`
  )
  if (savedState === 'hidden') {
    isContentVisible.value = false
  }
})

function openInNewTab(url: string) {
  window.open(url, '_blank')
}
</script>

<template>
  <div v-if="isContentVisible" class="help always_on">
    <div class="info_icon">
      <img class="icon" />
    </div>
    <div class="help_text">
      <p>{{ props.properties['i18n']['title'] }}</p>
      <p>{{ props.properties['i18n']['message'] }}</p>
      <div class="buttons">
        <!-- TODO: Change buttons to a new implementation -->
        <Button
          :label="properties['i18n']['setup_link_title']"
          @click="openInNewTab(properties['setup_link'])"
        />
        <Button :label="properties['i18n']['do_not_show_again_title']" @click="hideContent" />
      </div>
    </div>
  </div>
</template>

<style scoped>
div.help {
  display: flex;
  margin-bottom: 24px;

  div.info_icon img {
    content: var(--icon-info);
  }

  div.help_text {
    background-color: rgb(38 47 56);
    color: var(--white);
  }

  p {
    margin-left: var(--spacing);

    &:first-child {
      font-weight: var(--font-weight-bold);
    }

    &:last-child {
      padding-bottom: var(--spacing);
    }
  }

  a:first-child {
    margin-right: var(--spacing);
  }

  .button {
    background-color: rgb(6 103 193);
    color: var(--white);
    border: unset;
  }
}
</style>
