/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import CmkConfigurationEntityDropdown from './CmkConfigurationEntityDropdown.vue'

export default CmkConfigurationEntityDropdown
/**
 * @private These exports are an API violation and should not be used outside of this
 * module. They are currently still exported because of the current dependencies but
 * should be removed once that dependency is resolved.
 */
export type { EntityDescription, Payload } from './configuration_entity'
/** @private See above. */
export { configEntityAPI } from './configuration_entity'

export type { SetDataResult } from './api-result-types'
