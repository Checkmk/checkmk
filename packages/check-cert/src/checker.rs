// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use openssl::asn1::{Asn1Time, Asn1TimeRef};

#[derive(PartialEq, Eq)]
pub enum Validity {
    OK,
    Warn,
    Crit,
}

pub fn check_validity(x: &Asn1TimeRef, warn: &Asn1Time, crit: &Asn1Time) -> Validity {
    std::assert!(warn >= crit);

    if crit >= x {
        Validity::Crit
    } else if warn >= x {
        Validity::Warn
    } else {
        Validity::OK
    }
}

#[cfg(test)]
mod test_check_validity {
    use super::{check_validity, Validity};
    use openssl::asn1::Asn1Time;

    fn days_from_now(days: u32) -> Asn1Time {
        Asn1Time::days_from_now(days).unwrap()
    }

    #[test]
    fn test_check_validity_ok() {
        assert!(
            check_validity(
                days_from_now(30).as_ref(),
                &days_from_now(0),
                &days_from_now(0),
            ) == Validity::OK
        );
        assert!(
            check_validity(
                days_from_now(30).as_ref(),
                &days_from_now(15),
                &days_from_now(7),
            ) == Validity::OK
        );
    }

    #[test]
    fn test_check_validity_warn() {
        assert!(
            check_validity(
                days_from_now(10).as_ref(),
                &days_from_now(15),
                &days_from_now(7),
            ) == Validity::Warn
        );
    }

    #[test]
    fn test_check_validity_crit() {
        assert!(
            check_validity(
                days_from_now(3).as_ref(),
                &days_from_now(15),
                &days_from_now(7),
            ) == Validity::Crit
        );
        assert!(
            check_validity(
                days_from_now(3).as_ref(),
                &days_from_now(15),
                &days_from_now(15),
            ) == Validity::Crit
        );
    }
}
