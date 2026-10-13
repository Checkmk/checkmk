/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { expect, test } from 'vitest'

import { createRescheduleAction } from '@/monitoring/shared/components/action/actions/reschedule'

const ERROR_HEADING = untranslated('Could not reschedule the checks for the selected hosts')

function action(reschedule: () => Promise<number>) {
  return createRescheduleAction<string>({ reschedule, errorHeading: ERROR_HEADING })
}

test('a refused reschedule comes back as an error, not as a confirmation', async () => {
  const built = action(async () => {
    throw new CmkApiError('Forbidden', null, '', 403)
  })

  const feedback = await built.perform(['host-1'], built.defaultValues())

  expect(feedback).toEqual({
    variant: 'error',
    heading: ERROR_HEADING,
    message: 'Retry the command. If it keeps failing, check whether the site is running.'
  })
})
