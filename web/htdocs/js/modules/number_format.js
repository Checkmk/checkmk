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
