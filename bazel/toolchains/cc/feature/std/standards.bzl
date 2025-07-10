# Adapted from https://github.com/CACI-International/cpp-toolchain
CPP_STD = [
    "98",
    "03",
    "11",
    "14",
    "17",
    "20",
    "23",
]

C_STD = [
    "89",
    "99",
    "11",
    "17",
    "23",
]

STANDARDS_FEATURES = ["c{}".format(std) for std in C_STD] + ["cpp{}".format(std) for std in CPP_STD]
