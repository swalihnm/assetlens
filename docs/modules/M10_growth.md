# M10 Growth Markets case (GCC private wealth office)

**Method.** Cohort model: advisor hires, attrition, logistic AUM ramp, net revenue bps, cost per head by location, set-up and licence costs, regulatory capital, tax, discount rate 11%, Gordon terminal value. Monte Carlo over AUM per advisor, revenue bps, ramp, attrition, hiring and market path; staged-entry real option by simulation (pilot, expand if year-2 AUM clears a gate).

**Outputs.** `growth/business_case.py`, `growth/simulation.py`, Excel `Growth_Case` (live NPV/IRR formulas).

**Results and validation.** DIFC base case: NPV $170m, IRR 50%, payback 5.7 years, peak funding $35m, 93% of NPV is terminal value (explicit seven-year NPV $11m). Monte Carlo (1,000 paths): mean NPV $255m, P10 $3m, P90 $577m, 10% probability of loss. Staged entry has negative option value in all six gate/delay settings (-$51m to -$154m) because it delays a project that is positive in about 90% of paths. UAE 15% minimum top-up tax and KSA 20% (see DECISIONS.md). Excel NPV/IRR equal Python to machine precision for all three locations.

**Limitations.** All operating inputs are illustrative assumptions. Terminal value dominates. Tax rates come from secondary sources; confirm with a tax adviser.
