function scale_factor_prefix(value, base, prefixes = ["", "k", "M", "G", "T", "P"]) {
    let factor = base;
    let prefix = prefixes[prefixes.length - 1];

    for (const unit_prefix of prefixes.slice(0, -1)) {
        if (Math.abs(value) < factor) {
            prefix = unit_prefix;
            break;
        }
        factor *= base;
    }
    return [factor / base, prefix];
}

function drop_dotzero(value, digits = 2) {
    return value.toFixed(digits).replace(/\.0+$/, "");
}

export function fmt_number_with_precision(
    v,
    base = 1000,
    precision = 2,
    drop_zeroes = false,
    unit = ""
) {
    const [factor, prefix] = scale_factor_prefix(v, base);
    const value = v / factor;
    const number = drop_zeroes ? drop_dotzero(value, precision) : value.toFixed(precision);
    return `${number} ${prefix + unit}`;
}

export function fmt_bytes(b, base = 1024, precision = 2, unit = "B") {
    return fmt_number_with_precision(b, base, precision, false, unit);
}

export function fmt_nic_speed(speed) {
    const speedi = parseInt(speed);
    if (isNaN(speedi)) return speed;

    return fmt_number_with_precision(speedi, 1000, 2, false, "bit/s");
}

export function percent(perc, scientific_notation = false) {
    if (perc == 0) return "0%";
    let result = "";
    if (scientific_notation && Math.abs(perc) >= 100000) {
        result = scientific(perc, 1);
    } else if (Math.abs(perc) >= 100) {
        result = perc.toFixed(0);
    } else if (0 < Math.abs(perc) < 0.01) {
        result = perc.toFixed(7);
        if (parseFloat(result) == 0) return "0%";
        if (scientific_notation && Math.abs(perc) < 0.0001) {
            result = scientific(perc, 1);
        } else {
            result = result.replace(/0+$/, "");
        }
    } else {
        result = drop_dotzero(perc, 2);
    }

    if (Number.isInteger(parseFloat(result)) && perc < 100) result = result + ".0";

    return result + "%";
}

export function scientific(v, precision) {
    if (v == 0) return "0";
    if (v < 0) return "-" + scientific(-1 * v, precision);

    let [mantissa, exponent] = frexpb(v, 10);
    if (-3 <= exponent <= 4) return v.toFixed(Math.max(0, precision - exponent));
    return v.toExponetial(precision);
}

export function frexpb(x, base) {
    let exp = Math.floor(Math.log(x) / Math.log(base));
    let mantissa = x / base ** exp;
    if (mantissa < 1) {
        mantissa *= base;
        exp -= 1;
    }
    return [mantissa, exp];
}
