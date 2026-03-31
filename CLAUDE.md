# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
streamlit run compare.py
```

Settings persist automatically to `settings.json` on every sidebar interaction.

## Regenerating the CSV

The CSV (`Car Comparison - Sheet1.csv`) is the data source for `compare.py`. Two scripts maintain it:

- **`update_csv.py`** — recalculates derived columns (fuel cost per mile, used prices, resale, maintenance, insurance) from the raw CSV and rewrites it in-place. Run after changing pricing assumptions or adding rows manually.
- **`generate_rows.py`** — generates new CSV rows for additional vehicle trims and prints them to stdout. Output is intended to be appended to the CSV.

```bash
python update_csv.py
python generate_rows.py >> "Car Comparison - Sheet1.csv"
```

## Architecture

### Data pipeline
`Car Comparison - Sheet1.csv` → `load_data()` → filter → `compute_tco()` → visualizations

### Key constants in `update_csv.py`
- `GAS_PRICE = 4.40` ($/gallon)
- `ELEC_RATE = 0.21` ($/kWh)
- Used prices are hardcoded by `(year, make, model, trim)` in the `UP` dict, representing Pittsburgh market ~25K miles

### TCO calculation (`compare.py: compute_tco`)
- **Purchase price**: used price for ≤2024 models, MSRP for 2025–2026 (when `purchase_type = "Auto"`)
- **Resale**: derived from `Resale_7yr` CSV column; an implied annual depreciation rate is computed relative to purchase price (with an 88% sales tax/fee multiplier), then extrapolated to N years
- **Annual costs**: fuel + insurance + (maintenance_7yr / 7)
- **PV discount**: all future costs discounted at `discount_pct` using standard annuity factor

### CSV columns expected by `compare.py`
`MSRP_New_Est`, `Used_Price_Est_25K_mi`, `Resale_7yr`, `Scheduled_Maint_7yr`, `Unscheduled_Repair_7yr`, `Insurance_Annual`, `Fuel_cost_city_per_mile`, `Fuel_cost_hwy_per_mile`, `Physical_HVAC_Controls`, `AEB_Standard`, `ACC_Standard`, `AWD_Standard`, `CPO_Available`, `IIHS_Rating`, `RepairPal_5`, `Max_Cargo_cuft`, `Cargo_2nd_Row_cuft`, `Powertrain`
