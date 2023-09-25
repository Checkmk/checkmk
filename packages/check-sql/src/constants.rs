// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub mod log {
    use flexi_logger::{Cleanup, Criterion, Naming};
    pub const FILE_MAX_SIZE: Criterion = Criterion::Size(100000);
    pub const FILE_NAMING: Naming = Naming::Numbers;
    pub const FILE_CLEANUP: Cleanup = Cleanup::KeepLogFiles(5);
}
