/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { expect, test } from 'vitest'

import HostSlideInActions from '@/monitoring/all-hosts/components/slide-in/HostSlideInActions.vue'
import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'

const RUNNING_CLASS = 'cmk-button--running'

test('no button pulses while nothing is running', () => {
  render(HostSlideInActions)

  expect(screen.getByRole('button', { name: 'Reschedule check' })).not.toHaveClass(RUNNING_CLASS)
})

test('the running action pulses', () => {
  render(HostSlideInActions, { props: { runningActionId: RESCHEDULE_ACTION_ID } })

  expect(screen.getByRole('button', { name: 'Reschedule check' })).toHaveClass(RUNNING_CLASS)
  expect(screen.getByRole('button', { name: 'Acknowledge problem' })).not.toHaveClass(RUNNING_CLASS)
})
