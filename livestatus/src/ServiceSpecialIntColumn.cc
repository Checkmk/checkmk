// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ServiceSpecialIntColumn.h"

#include "Row.h"

#ifdef CMC
#include "Metric.h"
#include "Object.h"
#include "RRDInfo.h"
#include "State.h"
#include "cmc.h"
#else
#include "nagios.h"
#endif

int32_t ServiceSpecialIntColumn::getValue(
    Row row, const contact * /* auth_user */) const {
#ifdef CMC
    if (const auto *const object = columnData<Object>(row)) {
        switch (_type) {
            case Type::real_hard_state: {
                if (object->isCurrentStateOK()) {
                    return 0;
                }
                const auto *const state = object->state();
                return state->_state_type == StateType::hard
                           ? state->_current_state
                           : state->_last_hard_state;
            }
        }
    }
#else
    if (const auto* const svc = columnData<service>(row)) {
        switch (_type) {
            case Type::real_hard_state:
                if (svc->current_state == STATE_OK) {
                    return 0;
                }
                return svc->state_type == HARD_STATE ? svc->current_state
                                                     : svc->last_hard_state;
        }
    }
#endif
    return 0;
}
