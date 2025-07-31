/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type { Component } from 'vue'
import AddHost from '@/welcome/components/steps/AddHost.vue'
import ActivateChangesAndExploreHosts from '@/welcome/components/steps/ActivateChangesAndExploreHosts.vue'
import EnableNotifications from '@/welcome/components/steps/EnableNotifications.vue'
import CustomizeDashboard from '@/welcome/components/steps/CustomizeDashboard.vue'
import type { StageInformation } from 'cmk-shared-typing/typescript/welcome'

export type StepId = StageInformation['finished'][number]

export const stepComponents: { component: Component; stepNumber: number; stepId: StepId }[] = [
  { component: AddHost, stepNumber: 1, stepId: 'add_host' },
  {
    component: ActivateChangesAndExploreHosts,
    stepNumber: 2,
    stepId: 'activate_changes_and_explore_hosts'
  },
  { component: EnableNotifications, stepNumber: 3, stepId: 'enable_notifications' },
  { component: CustomizeDashboard, stepNumber: 4, stepId: 'customize_dashboard' }
]

export const totalSteps = stepComponents.length
