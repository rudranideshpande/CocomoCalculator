#!/usr/bin/env python3
"""
COCOMO Estimation Tool
Input : size in LoC (lines of code)
Output: Effort, Development Time, Staff for
        - Basic COCOMO        (all 3 modes)
        - Intermediate COCOMO (all 3 modes, EAF from 15 cost drivers)
        - Detailed COCOMO     (all 3 modes, phase-wise split)
        - COCOMO II Post-Architecture (bonus, nominal scale factors)
"""

import sys

# ---------------------------------------------------------------- constants
MODES = ["Organic", "Semi-Detached", "Embedded"]

# Basic COCOMO: a, b, c, d
BASIC = {
    "Organic":       (2.4, 1.05, 2.5, 0.38),
    "Semi-Detached": (3.0, 1.12, 2.5, 0.35),
    "Embedded":      (3.6, 1.20, 2.5, 0.32),
}

# Intermediate COCOMO: only 'a' changes (b, c, d same as Basic)
INTER_A = {"Organic": 3.2, "Semi-Detached": 3.0, "Embedded": 2.8}

# 15 cost drivers (Boehm 1981). Ratings: VL, L, N, H, VH, XH
COST_DRIVERS = {
    # Product
    "RELY": {"VL": 0.75, "L": 0.88, "N": 1.00, "H": 1.15, "VH": 1.40},
    "DATA": {"L": 0.94, "N": 1.00, "H": 1.08, "VH": 1.16},
    "CPLX": {"VL": 0.70, "L": 0.85, "N": 1.00, "H": 1.15, "VH": 1.30, "XH": 1.65},
    # Hardware
    "TIME": {"N": 1.00, "H": 1.11, "VH": 1.30, "XH": 1.66},
    "STOR": {"N": 1.00, "H": 1.06, "VH": 1.21, "XH": 1.56},
    "VIRT": {"L": 0.87, "N": 1.00, "H": 1.15, "VH": 1.30},
    "TURN": {"L": 0.87, "N": 1.00, "H": 1.07, "VH": 1.15},
    # Personnel
    "ACAP": {"VL": 1.46, "L": 1.19, "N": 1.00, "H": 0.86, "VH": 0.71},
    "AEXP": {"VL": 1.29, "L": 1.13, "N": 1.00, "H": 0.91, "VH": 0.82},
    "PCAP": {"VL": 1.42, "L": 1.17, "N": 1.00, "H": 0.86, "VH": 0.70},
    "VEXP": {"VL": 1.21, "L": 1.10, "N": 1.00, "H": 0.90},
    "LEXP": {"VL": 1.14, "L": 1.07, "N": 1.00, "H": 0.95},
    # Project
    "MODP": {"VL": 1.24, "L": 1.10, "N": 1.00, "H": 0.91, "VH": 0.82},
    "TOOL": {"VL": 1.24, "L": 1.10, "N": 1.00, "H": 0.91, "VH": 0.83},
    "SCED": {"VL": 1.23, "L": 1.08, "N": 1.00, "H": 1.04, "VH": 1.10},
}

# Detailed COCOMO: % of effort per phase, by mode and size class (KLOC).
# Plan&Req is added on top; the other three phases sum to 100 %.
# Columns: Plan&Req, Product Design, Programming, Integration&Test
DETAILED = {
    "Organic": {
        2:   (6, 16, 68, 16),
        8:   (6, 16, 65, 19),
        32:  (6, 16, 62, 22),
        128: (6, 16, 59, 25),
    },
    "Semi-Detached": {
        8:   (7, 17, 64, 19),
        32:  (7, 17, 61, 22),
        128: (7, 17, 58, 25),
        512: (7, 17, 55, 28),
    },
    "Embedded": {
        8:   (8, 18, 60, 22),
        32:  (8, 18, 57, 25),
        128: (8, 18, 54, 28),
        512: (8, 18, 51, 31),
    },
}
PHASES = ["Plan & Requirements", "Product Design", "Programming", "Integration & Test"]

# COCOMO II (2000) Post-Architecture, nominal scale factors
C2_A, C2_B, C2_C, C2_D = 2.94, 0.91, 3.67, 0.28
C2_SF_NOMINAL = {"PREC": 3.72, "FLEX": 3.04, "RESL": 4.24, "TEAM": 3.29, "PMAT": 4.68}


# ---------------------------------------------------------------- functions
def suggest_mode(kloc):
    """Mode by size, as in the GeeksforGeeks reference."""
    if kloc <= 50:
        return "Organic"
    if kloc <= 300:
        return "Semi-Detached"
    return "Embedded"


def basic(kloc, mode):
    a, b, c, d = BASIC[mode]
    effort = a * kloc ** b
    tdev = c * effort ** d
    return effort, tdev, effort / tdev


def compute_eaf(ratings):
    """ratings: dict driver -> rating code. Missing drivers = Nominal."""
    eaf = 1.0
    for drv, table in COST_DRIVERS.items():
        code = ratings.get(drv, "N")
        if code not in table:
            raise ValueError(f"Rating {code} not valid for {drv}; use {list(table)}")
        eaf *= table[code]
    return eaf


def intermediate(kloc, mode, eaf):
    _, b, c, d = BASIC[mode]
    effort = INTER_A[mode] * kloc ** b * eaf
    tdev = c * effort ** d
    return effort, tdev, effort / tdev


def detailed(kloc, mode, eaf):
    effort, tdev, staff = intermediate(kloc, mode, eaf)
    classes = DETAILED[mode]
    nearest = min(classes, key=lambda s: abs(s - kloc))
    pct = classes[nearest]
    # Programming + Design + I&T = 100 %; Plan&Req is extra on top
    phase_effort = [effort * p / 100 for p in pct]
    return effort, tdev, staff, nearest, pct, phase_effort


def cocomo2(kloc, eaf=1.0, sf=None):
    sf = sf or C2_SF_NOMINAL
    e = C2_B + 0.01 * sum(sf.values())
    pm = C2_A * eaf * kloc ** e
    f = C2_D + 0.2 * (e - C2_B)
    tdev = C2_C * pm ** f
    return pm, tdev, pm / tdev, e


# ---------------------------------------------------------------- UI helpers
def ask_ratings():
    print("\nRate each cost driver (VL/L/N/H/VH/XH), Enter = Nominal (N).")
    ratings = {}
    for drv, table in COST_DRIVERS.items():
        while True:
            ans = input(f"  {drv} {list(table)} [N]: ").strip().upper() or "N"
            if ans in table:
                ratings[drv] = ans
                break
            print("   invalid rating, try again")
    return ratings


def report(loc, ratings, rate=None):
    kloc = loc / 1000.0
    eaf = compute_eaf(ratings)
    print("\n" + "=" * 78)
    print(f"INPUT: {loc:,.0f} LoC = {kloc:g} KLOC   |  EAF = {eaf:.4f}"
          f"  |  size-based mode = {suggest_mode(kloc)}")
    print("=" * 78)

    def row(label, mode, e, t, s):
        cost = f"{e * rate:>14,.0f}" if rate else ""
        print(f"{label:<13}{mode:<15}{e:>12.2f}{t:>12.2f}{s:>9.2f}{cost}")

    hdr = f"{'Model':<13}{'Mode':<15}{'Effort(PM)':>12}{'Tdev(mo)':>12}{'Staff':>9}"
    if rate:
        hdr += f"{'Cost':>14}"
    print(hdr)
    print("-" * len(hdr))

    for m in MODES:
        row("Basic", m, *basic(kloc, m))
    print("-" * len(hdr))
    for m in MODES:
        row("Intermediate", m, *intermediate(kloc, m, eaf))
    print("-" * len(hdr))
    for m in MODES:
        e, t, s, *_ = detailed(kloc, m, eaf)
        row("Detailed", m, e, t, s)
    print("-" * len(hdr))
    e, t, s, exp = cocomo2(kloc, eaf)
    row("COCOMO II", f"E={exp:.4f}", e, t, s)

    print("\nDetailed COCOMO - phase-wise effort (person-months)")
    for m in MODES:
        e, t, s, near, pct, pe = detailed(kloc, m, eaf)
        print(f"\n  {m} (size class used: {near} KLOC)")
        for name, p, v in zip(PHASES, pct, pe):
            print(f"    {name:<22}{p:>4}%   {v:>12.2f} PM")


def main():
    # Attempt to parse command-line arguments for LoC values.
    # Filter out any arguments that cannot be converted to float.
    # This handles cases like '-f' from IPython/Colab environments.
    potential_locs = []
    for arg in sys.argv[1:]:
        try:
            potential_locs.append(float(arg))
        except ValueError:
            # Silently ignore arguments that are not valid floats
            # This is a common pattern for handling environment-specific arguments
            # like '-f' in sys.argv when running in IPython/Colab.
            pass

    if potential_locs:
        locs = potential_locs
        ratings = {}
        rate = None
    else:
        # If no valid float arguments were found, prompt the user for input.
        locs = [float(input("Enter size in LoC: "))]
        ratings = ask_ratings() if input("Set cost drivers? (y/N): ").lower() == "y" else {}
        r = input("Cost per person-month (Enter to skip): ").strip()
        rate = float(r) if r else None

    for loc in locs:
        report(loc, ratings, rate)


if __name__ == "__main__":
    main()