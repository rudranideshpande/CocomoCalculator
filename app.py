import pandas as pd
import streamlit as st

import cocomo as cc  

st.set_page_config(page_title="COCOMO Estimator", page_icon="📊", layout="wide")

GROUPS = {
    "Product": ["RELY", "DATA", "CPLX"],
    "Hardware": ["TIME", "STOR", "VIRT", "TURN"],
    "Personnel": ["ACAP", "AEXP", "PCAP", "VEXP", "LEXP"],
    "Project": ["MODP", "TOOL", "SCED"],
}
LABELS = {
    "RELY": "Required reliability", "DATA": "Database size", "CPLX": "Product complexity",
    "TIME": "Execution time constraint", "STOR": "Main storage constraint",
    "VIRT": "Virtual machine volatility", "TURN": "Computer turnaround time",
    "ACAP": "Analyst capability", "AEXP": "Applications experience",
    "PCAP": "Programmer capability", "VEXP": "Virtual machine experience",
    "LEXP": "Language experience", "MODP": "Modern programming practices",
    "TOOL": "Use of software tools", "SCED": "Required schedule",
}

# ------------------------------------------------------------------ sidebar
st.sidebar.title("⚙️ Inputs")
loc = st.sidebar.number_input("Project size (LoC)", min_value=100, value=50_000, step=1_000)
kloc = loc / 1000
auto_mode = cc.suggest_mode(kloc)
mode = st.sidebar.selectbox("Project mode", cc.MODES, index=cc.MODES.index(auto_mode),
                            help=f"Size-based suggestion: {auto_mode}")
currency = st.sidebar.text_input("Currency symbol", "₹")
rate = st.sidebar.number_input("Cost per person-month", min_value=0, value=0, step=5_000,
                               help="Leave 0 to hide cost")

st.sidebar.subheader("Cost drivers")
st.sidebar.caption("Used by Intermediate, Detailed and COCOMO II. N = Nominal.")
ratings = {}
for group, drivers in GROUPS.items():
    with st.sidebar.expander(group):
        for d in drivers:
            ratings[d] = st.selectbox(f"{d} – {LABELS[d]}", list(cc.COST_DRIVERS[d]),
                                      index=list(cc.COST_DRIVERS[d]).index("N"), key=d)
eaf = cc.compute_eaf(ratings)

# ------------------------------------------------------------------ header
st.title("📊 COCOMO Estimator")
st.caption("Basic · Intermediate · Detailed · COCOMO II")

# ------------------------------------------------------------------ results
e, t, s = cc.intermediate(kloc, mode, eaf)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Size", f"{kloc:g} KLOC")
c2.metric("EAF", f"{eaf:.3f}")
c3.metric("Effort (Intermediate)", f"{e:,.1f} PM")
c4.metric("Duration", f"{t:,.1f} months")
c5.metric("Avg. staff", f"{s:,.1f}")
if rate:
    st.success(f"Estimated cost ({mode}, Intermediate): **{currency}{e * rate:,.0f}**")

# All-model table
rows = []
for m in cc.MODES:
    rows.append(("Basic", m, *cc.basic(kloc, m)))
for m in cc.MODES:
    rows.append(("Intermediate", m, *cc.intermediate(kloc, m, eaf)))
for m in cc.MODES:
    rows.append(("Detailed", m, *cc.detailed(kloc, m, eaf)[:3]))
pm, td, st_, exp = cc.cocomo2(kloc, eaf)
rows.append(("COCOMO II", f"E={exp:.3f}", pm, td, st_))
df = pd.DataFrame(rows, columns=["Model", "Mode", "Effort (PM)", "Tdev (months)", "Staff"])
if rate:
    df["Cost"] = (df["Effort (PM)"] * rate).round(0)

tab1, tab2, tab3, tab4 = st.tabs(["Comparison", "Detailed phases", "Charts", "About"])

with tab1:
    st.dataframe(df.style.format({"Effort (PM)": "{:,.2f}", "Tdev (months)": "{:,.2f}",
                                  "Staff": "{:,.2f}", "Cost": "{:,.0f}"}),
                 use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download CSV", df.to_csv(index=False), "cocomo_estimate.csv", "text/csv")

with tab2:
    dm = st.radio("Mode", cc.MODES, index=cc.MODES.index(mode), horizontal=True)
    de, dt, ds, near, pct, pe = cc.detailed(kloc, dm, eaf)
    st.write(f"Size class used: **{near} KLOC** · Total effort **{de:,.2f} PM** · "
             f"Duration **{dt:,.2f} months**")
    ph = pd.DataFrame({"Phase": cc.PHASES, "Share (%)": pct, "Effort (PM)": pe})
    if rate:
        ph["Cost"] = ph["Effort (PM)"] * rate
    left, right = st.columns([1, 1])
    left.dataframe(ph, hide_index=True, use_container_width=True)
    right.bar_chart(ph.set_index("Phase")["Effort (PM)"])

with tab3:
    st.subheader("Effort by model and mode")
    st.bar_chart(df.pivot_table(index="Model", columns="Mode", values="Effort (PM)"))
    st.subheader("Effort vs. size (Intermediate, selected mode)")
    sizes = [max(1, kloc * f) for f in (0.25, 0.5, 0.75, 1, 1.25, 1.5, 2)]
    curve = pd.DataFrame({"KLOC": sizes,
                          "Effort (PM)": [cc.intermediate(k, mode, eaf)[0] for k in sizes]})
    st.line_chart(curve.set_index("KLOC"))

with tab4:
    st.markdown(
        "- **Basic**: `E = a·KLOC^b`, `T = c·E^d`\n"
        "- **Intermediate**: Basic × EAF (product of 15 cost drivers)\n"
        "- **Detailed**: Intermediate effort split across phases\n"
        "- **COCOMO II**: Post-Architecture with nominal scale factors\n\n"
        "Estimates are approximations; calibrate constants with your own project data."
    )
