#!/usr/bin/env python3
"""Generate CSV rows for additional models and append to car_comparison.csv."""

import csv

HEADERS = [
    "Year","Make","Model","Trim","Powertrain","Generation",
    "MSRP_New_Est","Used_Price_Est_50_60K_mi",
    "MPG_City","MPG_Hwy","MPG_Combined","Meets_MPG_35plus",
    "HP","AWD_Standard","EV_Range_mi","Battery_kWh",
    "AEB_Standard","ACC_Standard","AEB_ACC_Both_Std","Physical_HVAC",
    "Safety_Pkg","NHTSA_Overall","IIHS_Rating","RepairPal_5",
    "Cargo_2nd_Row_cuft","Max_Cargo_cuft","Towing_lbs","Ground_Clearance_in",
    "Purchase_w_Tax_Fees","Fuel_15yr","Maintenance_Tires_15yr",
    "Insurance_Annual","Insurance_15yr","Battery_Reserve",
    "Resale_15yr","Net_TCO_15yr",
    "Qualifies","Disqualifier","Notes"
]

def r(year, make, model, trim, pt, gen, msrp, used="",
       city="", hwy="", comb="", mpg35="",
       hp="", awd="Yes", ev="", bat="",
       aeb="Yes", acc="Yes", aebacc="Yes", hvac="Yes",
       pkg="", nhtsa="5★", iihs="", rp="",
       cargo_r="", cargo_max="", tow="", gc="",
       purch="", fuel15="", maint15="",
       ins_ann="", ins15="", bat_res="",
       resid="", tco="",
       qual="", disq="", notes=""):
    return {
        "Year": year, "Make": make, "Model": model, "Trim": trim,
        "Powertrain": pt, "Generation": gen,
        "MSRP_New_Est": msrp, "Used_Price_Est_50_60K_mi": used,
        "MPG_City": city, "MPG_Hwy": hwy, "MPG_Combined": comb,
        "Meets_MPG_35plus": mpg35,
        "HP": hp, "AWD_Standard": awd, "EV_Range_mi": ev, "Battery_kWh": bat,
        "AEB_Standard": aeb, "ACC_Standard": acc, "AEB_ACC_Both_Std": aebacc,
        "Physical_HVAC": hvac,
        "Safety_Pkg": pkg, "NHTSA_Overall": nhtsa, "IIHS_Rating": iihs,
        "RepairPal_5": rp,
        "Cargo_2nd_Row_cuft": cargo_r, "Max_Cargo_cuft": cargo_max,
        "Towing_lbs": tow, "Ground_Clearance_in": gc,
        "Purchase_w_Tax_Fees": purch, "Fuel_15yr": fuel15,
        "Maintenance_Tires_15yr": maint15,
        "Insurance_Annual": ins_ann, "Insurance_15yr": ins15,
        "Battery_Reserve": bat_res,
        "Resale_15yr": resid, "Net_TCO_15yr": tco,
        "Qualifies": qual, "Disqualifier": disq, "Notes": notes
    }

rows = []

# ──────────────────────────────────────────────────────────────────────
# HONDA CR-V  (5th gen 2017-2022, 6th gen 2023+)
# Honda Sensing (AEB+ACC): EX+ standard 2018-2019; ALL trims from 2020
# Hybrid: 2020+ only
# MPG gas AWD ~29 comb; Hybrid AWD ~38 comb
# ──────────────────────────────────────────────────────────────────────
crv_g5_gas = [  # (year, trim, msrp, aeb_std, acc_std, aacc_std, notes_extra)
    # 2018
    (2018,"LX","$27500","No","No","No","Honda Sensing not on LX 2018"),
    (2018,"EX","$29500","Yes","Yes","Yes",""),
    (2018,"EX-L","$31500","Yes","Yes","Yes",""),
    (2018,"Touring","$34500","Yes","Yes","Yes",""),
    # 2019
    (2019,"LX","$28000","No","No","No","Honda Sensing not on LX 2019"),
    (2019,"EX","$30000","Yes","Yes","Yes",""),
    (2019,"EX-L","$32000","Yes","Yes","Yes",""),
    (2019,"Touring","$35000","Yes","Yes","Yes",""),
    # 2020 – Honda Sensing std all
    (2020,"LX","$28500","Yes","Yes","Yes","Honda Sensing std all trims from 2020"),
    (2020,"EX","$30500","Yes","Yes","Yes",""),
    (2020,"EX-L","$32500","Yes","Yes","Yes",""),
    (2020,"Touring","$35500","Yes","Yes","Yes",""),
    # 2021
    (2021,"LX","$29000","Yes","Yes","Yes",""),
    (2021,"EX","$31000","Yes","Yes","Yes",""),
    (2021,"EX-L","$33000","Yes","Yes","Yes",""),
    (2021,"Touring","$36000","Yes","Yes","Yes",""),
    # 2022
    (2022,"LX","$29500","Yes","Yes","Yes","Last yr 5th gen gas"),
    (2022,"EX","$31500","Yes","Yes","Yes",""),
    (2022,"EX-L","$33500","Yes","Yes","Yes",""),
    (2022,"Touring","$37000","Yes","Yes","Yes",""),
]
for yr, trim, msrp, aeb, acc, aacc, note in crv_g5_gas:
    rows.append(r(yr,"Honda","CR-V",trim,"Gas","5th Gen",msrp,
        city=27,hwy=33,comb=29,mpg35="No",hp=190,awd="Yes (opt)",
        aeb=aeb,acc=acc,aebacc=aacc,hvac="Yes",
        pkg="Honda Sensing",nhtsa="5★",iihs="TSP+",rp="4.5/5.0",
        cargo_r=39.2,cargo_max=75.8,tow=1500,gc=7.8,
        qual="No",disq="Fails MPG (29)",notes=note))

# CR-V Gas 6th gen 2023-2026
crv_g6_gas_trims = [
    ("LX","$31000"),("EX","$33000"),("EX-L","$35500"),
    ("Sport","$34000"),("Sport-L","$37000"),("Sport Touring","$40000"),
]
for yr in range(2023, 2027):
    suffix = "Verify specs" if yr >= 2025 else ""
    gen = "6th Gen"
    for trim, msrp in crv_g6_gas_trims:
        offset = (yr - 2023) * 500
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        rows.append(r(yr,"Honda","CR-V",trim,"Gas",gen,adjusted,
            city=27,hwy=33,comb=29,mpg35="No",hp=192,awd="Yes (opt)",
            pkg="Honda Sensing",nhtsa="5★",iihs="TSP+",rp="4.5/5.0",
            cargo_r=39.3,cargo_max=76.5,tow=1500,gc=7.8,
            qual="No",disq="Fails MPG (29)",notes=suffix))

# CR-V Hybrid 5th gen 2020-2022
crv_hyb_g5 = [
    (2020,"EX","$31000","$23000"),
    (2020,"EX-L","$33500","$24500"),
    (2020,"Touring","$37000",""),
    (2021,"EX","$32000","$24500"),
    (2021,"EX-L","$34500","$25500"),
    (2021,"Touring","$38000",""),
    (2022,"EX","$33000",""),
    (2022,"EX-L","$35500",""),
    (2022,"Touring","$39000",""),
]
for yr, trim, msrp, used in crv_hyb_g5:
    # from user research: 2020 ~$23k used, 2021 ~$24.5k used
    purch = used if used else ""
    fuel = "$22321" if used else ""
    maint = "$11450" if used else ""
    ins = "$1700"
    ins15 = "$25500"
    bat = "$1400" if used else ""
    resid = "-$2000" if yr == 2020 else ("-$2500" if yr == 2021 else "")
    tco = "$81671" if (yr == 2020 and trim == "EX") else ("$82671" if (yr == 2021 and trim == "EX") else "")
    rows.append(r(yr,"Honda","CR-V",f"{trim} Hybrid","Hybrid","5th Gen",msrp,used,
        city=40,hwy=35,comb=38,mpg35="Yes",hp=212,awd="Yes",bat=1.4,
        pkg="Honda Sensing",nhtsa="5★",iihs="TSP+",rp="4.5/5.0",
        cargo_r=39.2,cargo_max=75.8,tow=1500,gc=7.8,
        purch=purch,fuel15=fuel,maint15=maint,
        ins_ann=ins,ins15=ins15,bat_res=bat,resid=resid,tco=tco,
        qual="Yes",notes="From prior research" if used else ""))

# CR-V Hybrid 6th gen 2023-2026 (improved MPG ~42 combined)
crv_hyb_g6_trims = [
    ("EX-L","$37500"),("Sport-L","$40000"),("Sport Touring","$43000"),
]
for yr in range(2023, 2027):
    suffix = "Verify specs" if yr >= 2025 else ""
    for trim, msrp in crv_hyb_g6_trims:
        offset = (yr - 2023) * 600
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        rows.append(r(yr,"Honda","CR-V",f"{trim} Hybrid","Hybrid","6th Gen",adjusted,
            city=43,hwy=36,comb=40,mpg35="Yes",hp=204,awd="Yes",bat=1.4,
            pkg="Honda Sensing",nhtsa="5★",iihs="TSP+",rp="4.5/5.0",
            cargo_r=39.3,cargo_max=76.5,tow=1500,gc=7.8,
            qual="Yes",notes=suffix))

# ──────────────────────────────────────────────────────────────────────
# FORD ESCAPE
# Co-Pilot360 (AEB std): 2020+; 2018-2019 had optional pre-collision only
# Hybrid & PHEV: 2020+
# ──────────────────────────────────────────────────────────────────────
# Gas 2018-2019 (3rd gen)
esc_g3_trims_18_19 = [
    ("S","1.5T","$24500",26,31,28,"FWD only on S"),
    ("SE","1.5T","$28000",26,31,28,"AWD opt"),
    ("SEL","1.5T/2.0T","$31000",22,29,25,"2.0T MPG shown; AWD opt"),
    ("Titanium","2.0T","$34000",22,29,25,"AWD opt"),
]
for yr in [2018, 2019]:
    for trim, eng, msrp, city, hwy, comb, note in esc_g3_trims_18_19:
        rows.append(r(yr,"Ford","Escape",trim,f"Gas {eng}","3rd Gen",msrp,
            city=city,hwy=hwy,comb=comb,mpg35="No",hp=179 if "1.5T" in eng else 245,
            awd="No (S) / opt" if trim=="S" else "Yes (opt)",
            aeb="No (opt)",acc="No (opt)",aebacc="No (opt)",hvac="Yes",
            pkg="Optional ADAS pkg",nhtsa="5★",iihs="",rp="",
            cargo_r=34.4,cargo_max=67.8,tow=1500,gc=7.9,
            qual="No",disq="Fails MPG; AEB/ACC optional only",notes=note))

# Gas 2020-2022 (4th gen) — Co-Pilot360 std
esc_g4_gas = [
    ("S","1.5T","$25500",27,33,30),
    ("SE","1.5T","$28500",27,33,30),
    ("SE Sport","2.0T","$32000",22,29,25),
    ("SEL","1.5T","$31000",27,33,30),
    ("Titanium","2.0T","$36000",22,29,25),
]
for yr in [2020, 2021, 2022]:
    for trim, eng, msrp, city, hwy, comb in esc_g4_gas:
        offset = (yr - 2020) * 500
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        rows.append(r(yr,"Ford","Escape",trim,f"Gas {eng}","4th Gen",adjusted,
            city=city,hwy=hwy,comb=comb,mpg35="No",
            hp=181 if "1.5T" in eng else 250,awd="Yes (opt)",
            pkg="Co-Pilot360",nhtsa="5★",iihs="",rp="",
            cargo_r=37.5,cargo_max=65.4,tow=1500 if "1.5T" in eng else 2000,gc=7.9,
            qual="No",disq="Fails MPG; poor reliability (CR)",
            notes="Co-Pilot360 std 2020+"))

# Escape Hybrid 2020-2022
esc_hyb = [
    (2020,"SE","$29000","$18000"),
    (2020,"SEL","$33000",""),
    (2020,"Titanium","$37000",""),
    (2021,"SE","$30000",""),
    (2021,"SEL","$34000",""),
    (2021,"Titanium","$38000",""),
    (2022,"SE","$31000",""),
    (2022,"SEL","$35000",""),
    (2022,"Titanium","$39000",""),
]
for yr, trim, msrp, used in esc_hyb:
    purch = used if used else ""
    fuel = "$20688" if used else ""
    maint = "$14450" if used else ""
    ins15 = "$27000"
    tco = "$82138" if (yr==2020 and trim=="SE" and used) else ""
    rows.append(r(yr,"Ford","Escape",f"{trim} Hybrid","Hybrid","4th Gen",msrp,used,
        city=44,hwy=37,comb=41,mpg35="Yes",hp=200,awd="Yes (opt)",bat=1.1,
        pkg="Co-Pilot360",nhtsa="5★",iihs="TSP (some configs)",rp="",
        cargo_r=37.5,cargo_max=65.4,tow=1500,gc=7.9,
        purch=purch,fuel15=fuel,maint15=maint,ins15=ins15,tco=tco,
        qual="Yes (with caveats)",disq="",
        notes="Poor CR reliability; from prior research" if used else "Poor CR reliability"))

# Escape PHEV 2020-2022
for yr in [2020, 2021, 2022]:
    offset = (yr - 2020) * 600
    rows.append(r(yr,"Ford","Escape","Titanium PHEV","PHEV","4th Gen",
        f"${39000+offset:,}","",
        city=100,hwy=84,comb="100 MPGe/40",mpg35="Yes",
        hp=209,awd="No (FWD only)",ev=37,bat=14.4,
        pkg="Co-Pilot360",nhtsa="5★",iihs="",rp="",
        cargo_r=33.5,cargo_max=60.8,tow=1500,gc=7.9,
        qual="Yes (with caveats)",disq="FWD only; poor CR reliability",
        notes="FWD only limits winter use"))

# Escape 2023-2026 (verify — potential discontinuation after 2023 in NA)
for yr in [2023, 2024, 2025, 2026]:
    for trim, msrp in [("SE","$30000"),("ST-Line","$33000"),("SEL","$35000"),("Titanium","$38000")]:
        offset = (yr - 2023) * 500
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        rows.append(r(yr,"Ford","Escape",trim,"Gas","4th Gen",adjusted,
            comb=30,mpg35="No",hp=181,awd="Yes (opt)",
            pkg="Co-Pilot360",nhtsa="5★",rp="",
            cargo_r=37.5,cargo_max=65.4,tow=1500,gc=7.9,
            qual="No",disq="Fails MPG; poor CR reliability",
            notes="Verify — check if Escape continues in NA"))
    for trim, msrp in [("SE Hybrid","$32000"),("SEL Hybrid","$36000"),("Titanium Hybrid","$40000")]:
        offset = (yr - 2023) * 600
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        rows.append(r(yr,"Ford","Escape",trim,"Hybrid","4th Gen",adjusted,
            city=44,hwy=37,comb=41,mpg35="Yes",hp=200,awd="Yes (opt)",bat=1.1,
            pkg="Co-Pilot360",nhtsa="5★",rp="",
            qual="Yes (with caveats)",disq="Poor CR reliability",
            notes="Verify — check if Escape continues in NA"))

# ──────────────────────────────────────────────────────────────────────
# TOYOTA VENZA (relaunched 2021, hybrid-only)
# Physical HVAC only on LE/XLE; XSE/Limited have touch-centric HVAC
# ──────────────────────────────────────────────────────────────────────
venza_trims = [
    ("LE","$33000","Yes","Yes","TSP"),
    ("XLE","$36000","Yes","Yes","TSP"),
    ("XSE","$38500","No (touch screen)","Yes (with caveat)","TSP"),
    ("Limited","$41500","No (touch screen)","No","TSP"),
]
for yr in range(2021, 2027):
    suffix = "Verify specs" if yr >= 2025 else ""
    for trim, msrp, hvac, qual, iihs in venza_trims:
        offset = (yr - 2021) * 500
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        # from prior research for 2021 LE
        purch = "$22000" if (yr == 2021 and trim == "LE") else ""
        fuel = "$21749" if (yr == 2021 and trim == "LE") else ""
        maint = "$12200" if (yr == 2021 and trim == "LE") else ""
        ins15 = "$28500" if (yr == 2021 and trim == "LE") else ""
        bat_res = "$1200" if (yr == 2021 and trim == "LE") else ""
        resid = "-$2500" if (yr == 2021 and trim == "LE") else ""
        tco = "$83149" if (yr == 2021 and trim == "LE") else ""
        disq = "" if qual == "Yes" else ("Fails Physical HVAC" if hvac.startswith("No") else "")
        rows.append(r(yr,"Toyota","Venza",trim,"Hybrid","2nd Gen",adjusted,
            city=40,hwy=37,comb=39,mpg35="Yes",hp=219,awd="Yes",bat=1.2,
            aeb="Yes",acc="Yes",aebacc="Yes",hvac=hvac,
            pkg="TSS 2.0",nhtsa="5★",iihs=iihs,rp="4.0/5.0",
            cargo_r=36.3,cargo_max=70.0,tow=1750,gc=8.1,
            purch=purch,fuel15=fuel,maint15=maint,ins15=ins15,
            bat_res=bat_res,resid=resid,tco=tco,
            qual=qual,disq=disq,
            notes=("From prior research" if purch else "") + (" Verify specs" if suffix else "").strip()))

# ──────────────────────────────────────────────────────────────────────
# MAZDA CX-5  (gas only; no hybrid)
# i-Activsense (AEB+ACC): std on Touring+ from 2018; all trims from 2019
# Physical HVAC: Yes all years
# All fail MPG ~27-29 combined
# ──────────────────────────────────────────────────────────────────────
cx5_2018 = [
    ("Sport","2.0L FWD/AWD","$26000",27,35,31,181,"FWD std; AWD opt on Sport"),
    ("Touring","2.5L AWD","$28500",26,31,28,187,"AWD std from Touring; AEB+ACC std"),
    ("Grand Touring","2.5L AWD","$31500",26,31,28,187,""),
    ("Grand Touring Reserve","2.5L AWD","$34500",26,31,28,187,""),
    ("Signature","2.5T AWD","$37500",24,30,26,227,"Turbo; i-Activsense std"),
]
for trim, eng, msrp, city, hwy, comb, hp, note in cx5_2018:
    aeb = "No (opt)" if trim == "Sport" else "Yes"
    acc = "No (opt)" if trim == "Sport" else "Yes"
    aacc = "No (opt)" if trim == "Sport" else "Yes"
    rows.append(r(2018,"Mazda","CX-5",trim,f"Gas {eng}","2nd Gen",msrp,
        city=city,hwy=hwy,comb=comb,mpg35="No",hp=hp,awd="Yes" if "AWD" in eng else "Yes (opt)",
        aeb=aeb,acc=acc,aebacc=aacc,hvac="Yes",
        pkg="i-Activsense",nhtsa="5★",iihs="TSP+",rp="4.5/5.0",
        cargo_r=30.9,cargo_max=59.6,tow=2000,gc=8.5,
        qual="No",disq=f"Fails MPG ({comb})",notes=note))

cx5_std_trims = [
    ("Sport","2.5L FWD/AWD","$27500",26,31,28,187,"AWD opt"),
    ("Touring","2.5L AWD","$29500",26,31,28,187,""),
    ("Carbon Edition","2.5L AWD","$33000",26,31,28,187,"Limited special edition; varies by year"),
    ("Grand Touring","2.5L AWD","$32000",26,31,28,187,""),
    ("Grand Touring Reserve","2.5L AWD","$35000",26,31,28,187,""),
    ("Signature","2.5T AWD","$38500",24,30,26,227,"Turbo; Sport mode available"),
]
for yr in range(2019, 2023):
    for trim, eng, msrp, city, hwy, comb, hp, note in cx5_std_trims:
        if trim == "Carbon Edition" and yr < 2021:
            continue  # Carbon Edition introduced around 2021
        offset = (yr - 2019) * 400
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        # from prior research: 2022 AWD $20k used, TCO $88,823
        used = "$20000" if yr == 2022 and trim in ("Grand Touring","Grand Touring Reserve") else ""
        rows.append(r(yr,"Mazda","CX-5",trim,f"Gas {eng}","2nd Gen",adjusted,used,
            city=city,hwy=hwy,comb=comb,mpg35="No",hp=hp,
            awd="Yes" if "AWD" in eng else "Yes (opt)",
            pkg="i-Activsense",nhtsa="5★",iihs="TSP+",rp="4.5/5.0",
            cargo_r=30.9,cargo_max=59.6,tow=2000,gc=8.5,
            qual="No",disq=f"Fails MPG ({comb})",notes=note))

# CX-5 2023-2026 (updated trims)
cx5_new_trims = [
    ("2.5 S","2.5L AWD","$29500",26,31,28,187,""),
    ("2.5 Select","2.5L AWD","$31000",26,31,28,187,""),
    ("2.5 Preferred","2.5L AWD","$33000",26,31,28,187,""),
    ("2.5 Preferred Plus","2.5L AWD","$35000",26,31,28,187,""),
    ("2.5 S Carbon Edition","2.5L AWD","$34000",26,31,28,187,"Limited edition"),
    ("2.5 GT","2.5L AWD","$36000",26,31,28,187,""),
    ("2.5 Turbo","2.5T AWD","$39000",24,30,26,256,"Updated turbo for 2023+"),
    ("2.5 Turbo Signature","2.5T AWD","$42000",24,30,26,256,"Top trim"),
]
for yr in range(2023, 2027):
    suffix = "Verify specs" if yr >= 2025 else ""
    # from user 2nd table: CX-5 Preferred CPO $26,850 used
    used_preferred = "$26850" if yr == 2023 else ""
    for trim, eng, msrp, city, hwy, comb, hp, note in cx5_new_trims:
        offset = (yr - 2023) * 400
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        used = used_preferred if ("Preferred" in trim and yr == 2023 and "Plus" not in trim) else ""
        rows.append(r(yr,"Mazda","CX-5",trim,f"Gas {eng}","2nd Gen",adjusted,used,
            city=city,hwy=hwy,comb=comb,mpg35="No",hp=hp,
            awd="Yes",pkg="i-Activsense",nhtsa="5★",iihs="TSP+",rp="4.5/5.0",
            cargo_r=30.9,cargo_max=59.6,tow=2000,gc=8.5,
            qual="No",disq=f"Fails MPG ({comb})",
            notes=((note+" " if note else "") + suffix).strip()))

# ──────────────────────────────────────────────────────────────────────
# HYUNDAI TUCSON
# 4th gen (2018-2021): gas only; SmartSense varies by trim/year
# 5th gen (2022+): gas/hybrid/PHEV; HVAC is all-touch (disqualifier)
# ──────────────────────────────────────────────────────────────────────
# 4th gen gas 2018-2021
tucson_g4 = [
    ("SE","2.0L FWD/AWD","$24000",23,30,26,161,"FWD std; AWD opt; no SmartSense"),
    ("Value","2.0L AWD","$25500",22,28,25,161,"AWD; no SmartSense"),
    ("SEL","2.0L AWD","$27000",22,28,25,161,"AWD; SmartSense opt"),
    ("Sport","1.6T AWD","$29000",25,30,27,175,"Turbo; SmartSense opt"),
    ("Night","1.6T AWD","$30500",25,30,27,175,"Sport appearance pkg"),
    ("Ultimate","1.6T AWD","$33000",25,30,27,175,"SmartSense std on Ultimate"),
]
for yr in range(2018, 2022):
    for trim, eng, msrp, city, hwy, comb, hp, note in tucson_g4:
        offset = (yr - 2018) * 400
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        aeb = "Yes" if trim == "Ultimate" else "No (opt)"
        acc = "Yes" if trim == "Ultimate" else "No (opt)"
        aacc = "Yes" if trim == "Ultimate" else "No (opt)"
        rows.append(r(yr,"Hyundai","Tucson",trim,f"Gas {eng}","4th Gen",adjusted,
            city=city,hwy=hwy,comb=comb,mpg35="No",hp=hp,
            awd="Yes" if "AWD" in eng else "Yes (opt)",
            aeb=aeb,acc=acc,aebacc=aacc,hvac="Yes",
            pkg="Hyundai SmartSense (opt/std)",nhtsa="5★",iihs="TSP+",rp="3.5/5.0",
            cargo_r=31.0,cargo_max=61.9,tow=1500,gc=6.9,
            qual="No",
            disq="Fails MPG" + ("; AEB/ACC not standard" if aacc != "Yes" else ""),
            notes=note))

# 5th gen 2022+ gas — all-touch HVAC disqualifies
tucson_g5_gas = [
    ("SE","2.5L AWD","$28000",26,33,28,187,""),
    ("SEL","2.5L AWD","$30000",26,33,28,187,""),
    ("N Line","2.5T AWD","$34000",22,28,25,277,"Turbo"),
    ("SEL Convenience","2.5L AWD","$32000",26,33,28,187,""),
    ("XRT","2.5L AWD","$33000",26,33,28,187,"Off-road appearance"),
    ("Limited","2.5L AWD","$37000",26,33,28,187,""),
]
for yr in range(2022, 2027):
    suffix = "Verify specs" if yr >= 2025 else ""
    for trim, eng, msrp, city, hwy, comb, hp, note in tucson_g5_gas:
        offset = (yr - 2022) * 500
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        rows.append(r(yr,"Hyundai","Tucson",trim,f"Gas {eng}","5th Gen",adjusted,
            city=city,hwy=hwy,comb=comb,mpg35="No",hp=hp,awd="Yes",
            hvac="No (all-touch)",
            pkg="Hyundai SmartSense",nhtsa="5★",iihs="TSP+",rp="3.5/5.0",
            cargo_r=31.9,cargo_max=66.3,tow=2000,gc=7.1,
            qual="No",disq="Fails MPG; Fails Physical HVAC",
            notes=(note + " " + suffix).strip()))

# 5th gen 2022+ Hybrid (1.6T hybrid, 227hp, ~38 combined AWD)
tucson_g5_hyb = [
    ("Blue","$33000"),("SEL","$36000"),
    ("N Line","$38000"),("SEL Convenience","$37500"),("Limited","$42000"),
]
for yr in range(2022, 2027):
    suffix = "Verify specs" if yr >= 2025 else ""
    used_2022 = {"Blue": "$20000"}
    for trim, msrp in tucson_g5_hyb:
        offset = (yr - 2022) * 500
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        used = used_2022.get(trim, "") if yr == 2022 else ""
        purch = used if used else ""
        fuel = "$22472" if purch else ""
        maint = "$13000" if purch else ""
        ins15 = "$25500" if purch else ""
        bat_res = "$2000" if purch else ""
        resid = "-$2000" if purch else ""
        tco = "$80972" if (yr == 2022 and trim == "Blue" and purch) else ""
        rows.append(r(yr,"Hyundai","Tucson",f"{trim} Hybrid","Hybrid","5th Gen",adjusted,used,
            city=38,hwy=38,comb=38,mpg35="Yes",hp=227,awd="Yes",bat=1.5,
            hvac="No (all-touch)",
            pkg="Hyundai SmartSense",nhtsa="5★",iihs="TSP+",rp="3.5/5.0",
            cargo_r=31.9,cargo_max=66.3,tow=3000,gc=7.1,
            purch=purch,fuel15=fuel,maint15=maint,ins15=ins15,
            bat_res=bat_res,resid=resid,tco=tco,
            qual="No",disq="Fails Physical HVAC (all-touch screen)",
            notes=("From prior research" if purch else "") + (" Verify specs" if suffix else "").strip()))

# 5th gen 2022+ PHEV
for yr in range(2022, 2027):
    suffix = "Verify specs" if yr >= 2025 else ""
    for trim, msrp in [("SEL PHEV","$39000"),("Limited PHEV","$46000")]:
        offset = (yr - 2022) * 600
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        rows.append(r(yr,"Hyundai","Tucson",trim,"PHEV","5th Gen",adjusted,
            city=80,hwy=76,comb="80 MPGe/35 gas",mpg35="Yes",hp=261,awd="Yes",
            ev=33,bat=13.8,hvac="No (all-touch)",
            pkg="Hyundai SmartSense",nhtsa="5★",iihs="",rp="3.5/5.0",
            cargo_r=29.6,cargo_max=63.2,tow=1650,gc=7.1,
            qual="No",disq="Fails Physical HVAC",
            notes=("Verify specs" if suffix else "")))

# ──────────────────────────────────────────────────────────────────────
# KIA SPORTAGE
# 4th gen (2017-2022): gas only
# 5th gen (2023+): gas/hybrid/PHEV; capacitive touch HVAC (disqualifier)
# ACC on hybrid: SX Prestige only (user's disqualifier)
# ──────────────────────────────────────────────────────────────────────
sport_g4 = [
    ("LX","2.4L FWD/AWD","$24500",23,30,26,181,"AWD opt; Drive Wise not std"),
    ("S","2.4L AWD","$26500",22,28,25,181,"AWD; Drive Wise not std"),
    ("EX","2.4L AWD","$28500",22,28,25,181,"Drive Wise std on EX"),
    ("SX","2.0T AWD","$30500",21,27,24,237,"Turbo; Drive Wise std"),
    ("SX Turbo","2.0T AWD","$33500",21,27,24,237,"Top trim"),
]
for yr in range(2018, 2023):
    for trim, eng, msrp, city, hwy, comb, hp, note in sport_g4:
        offset = (yr - 2018) * 400
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        aeb = "Yes" if trim in ("EX","SX","SX Turbo") else "No (opt)"
        acc = "Yes" if trim in ("EX","SX","SX Turbo") else "No (opt)"
        aacc = "Yes" if trim in ("EX","SX","SX Turbo") else "No (opt)"
        rows.append(r(yr,"Kia","Sportage",trim,f"Gas {eng}","4th Gen",adjusted,
            city=city,hwy=hwy,comb=comb,mpg35="No",hp=hp,
            awd="Yes" if "AWD" in eng else "Yes (opt)",
            aeb=aeb,acc=acc,aebacc=aacc,hvac="Yes",
            pkg="Kia Drive Wise",nhtsa="5★",iihs="",rp="3.5/5.0",
            cargo_r=30.7,cargo_max=62.8,tow=2000,gc=8.1,
            qual="No",
            disq="Fails MPG" + ("; AEB/ACC not standard" if aacc != "Yes" else ""),
            notes=note))

# 5th gen 2023+ gas (capacitive HVAC)
sport_g5_gas = [
    ("LX","2.5L AWD","$29000",26,33,29,187,""),
    ("S","2.5L AWD","$31000",26,33,29,187,""),
    ("EX","2.5L AWD","$33000",26,33,29,187,""),
    ("X-Pro","2.5L AWD","$34500",25,31,28,187,"Off-road focus"),
    ("SX Prestige","2.5T AWD","$38000",22,28,24,277,"Turbo; top gas trim"),
]
for yr in range(2023, 2027):
    suffix = "Verify specs" if yr >= 2025 else ""
    for trim, eng, msrp, city, hwy, comb, hp, note in sport_g5_gas:
        offset = (yr - 2023) * 400
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        rows.append(r(yr,"Kia","Sportage",trim,f"Gas {eng}","5th Gen",adjusted,
            city=city,hwy=hwy,comb=comb,mpg35="No",hp=hp,awd="Yes",
            hvac="No (capacitive touch)",
            pkg="Kia Drive Wise",nhtsa="5★",iihs="",rp="3.5/5.0",
            cargo_r=31.0,cargo_max=63.5,tow=2000,gc=8.1,
            qual="No",disq="Fails MPG; Fails Physical HVAC",
            notes=((note + " " if note else "") + suffix).strip()))

# 5th gen 2023+ Hybrid
sport_g5_hyb = [
    ("LX Hybrid","$33500","No (LX)"),
    ("EX Hybrid","$36000","No (EX)"),
    ("SX Prestige Hybrid","$39000","Yes (SX Pres only)"),
]
for yr in range(2023, 2027):
    suffix = "Verify specs" if yr >= 2025 else ""
    used_2023 = {"SX Prestige Hybrid": "$22000"}
    for trim, msrp, acc_note in sport_g5_hyb:
        offset = (yr - 2023) * 500
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        used = used_2023.get(trim, "") if yr == 2023 else ""
        purch = used if used else ""
        fuel = "$22472" if purch else ""
        maint = "$13000" if purch else ""
        ins15 = "$25500"
        bat_res = "$2000" if purch else ""
        resid = "-$2000" if purch else ""
        tco = "$83972" if (yr == 2023 and "SX Prestige" in trim and purch) else ""
        acc_std = "Yes" if "SX Prestige" in trim else "No (std on SX Prestige only)"
        aacc_std = "Yes" if "SX Prestige" in trim else "No"
        disq = "Fails Physical HVAC" + ("" if "SX Prestige" in trim else "; ACC not standard")
        rows.append(r(yr,"Kia","Sportage",trim,"Hybrid","5th Gen",adjusted,used,
            city=39,hwy=38,comb=38,mpg35="Yes",hp=227,awd="Yes",bat=1.5,
            acc=acc_std,aebacc=aacc_std,
            hvac="No (capacitive touch)",
            pkg="Kia Drive Wise",nhtsa="5★",iihs="",rp="3.5/5.0",
            cargo_r=31.0,cargo_max=63.5,tow=1650,gc=8.1,
            purch=purch,fuel15=fuel,maint15=maint,ins15=ins15,
            bat_res=bat_res,resid=resid,tco=tco,
            qual="No",disq=disq,
            notes=f"ACC: {acc_note}" + (" From prior research" if purch else "") + (" Verify specs" if suffix else "")))

# ──────────────────────────────────────────────────────────────────────
# TOYOTA C-HR (US: 2018-2022, FWD only, discontinued in US after 2022)
# ──────────────────────────────────────────────────────────────────────
chr_trims_by_year = {
    2018: [("LE","$22000"),("XLE","$24000"),("XLE Premium","$26000"),("Limited","$28000")],
    2019: [("LE","$22500"),("XLE","$24500"),("XLE Premium","$26500"),("Limited","$28500")],
    2020: [("LE","$23000"),("XLE","$25000"),("Nightshade","$26000"),("Limited","$29000")],
    2021: [("LE","$23500"),("XLE","$25500"),("Nightshade","$26500"),("Limited","$29500")],
    2022: [("LE","$24000"),("XLE","$26000"),("Nightshade","$27000"),("Limited","$30000")],
}
for yr, trims in chr_trims_by_year.items():
    for trim, msrp in trims:
        used = "$18000" if (yr == 2021 and trim == "LE") else ""
        purch = used
        fuel = "$27709" if purch else ""
        maint = "$11450" if purch else ""
        ins15 = "$22500" if purch else ""
        resid = "-$1500" if purch else ""
        tco = "$78159" if purch else ""
        rows.append(r(yr,"Toyota","C-HR",trim,"Gas","1st Gen",msrp,used,
            city=27,hwy=31,comb=29,mpg35="No",hp=144,awd="No (FWD only)",
            pkg="TSS 2.0",nhtsa="4★",iihs="TSP",rp="4.0/5.0",
            cargo_r=19.0,cargo_max=36.4,tow="N/A",gc=6.9,
            purch=purch,fuel15=fuel,maint15=maint,ins15=ins15,resid=resid,tco=tco,
            qual="No",disq="Fails MPG (29); FWD only; small cargo",
            notes="From prior research" if purch else "Discontinued US after 2022"))

# ──────────────────────────────────────────────────────────────────────
# TOYOTA COROLLA CROSS
# Gas (2022+): 2.0L, ~29 combined, AWD opt
# Hybrid (2024+): ~42 combined, AWD std
# ──────────────────────────────────────────────────────────────────────
ccross_gas_trims = [("L","$24000"),("LE","$26500"),("XSE","$29000")]
for yr in range(2022, 2027):
    suffix = "Verify specs" if yr >= 2025 else ""
    for trim, msrp in ccross_gas_trims:
        offset = (yr - 2022) * 400
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        rows.append(r(yr,"Toyota","Corolla Cross",trim,"Gas","1st Gen",adjusted,
            city=29,hwy=35,comb=31,mpg35="No",hp=169,awd="Yes (opt)",
            pkg="TSS 2.0",nhtsa="5★",iihs="TSP",rp="4.0/5.0",
            cargo_r=24.3,cargo_max=46.0,tow=1500,gc=8.3,
            qual="No",disq="Fails MPG (31)",
            notes=("Smaller than RAV4/Forester " + suffix).strip()))

# Corolla Cross Hybrid 2024+
ccross_hyb_trims = [("S","$29500"),("SE","$31500"),("XSE","$33000")]
for yr in range(2024, 2027):
    suffix = "Verify specs" if yr >= 2025 else ""
    for trim, msrp in ccross_hyb_trims:
        offset = (yr - 2024) * 500
        adjusted = f"${int(msrp[1:].replace(',','')) + offset:,}"
        # from user 2nd table: new Corolla Cross Hybrid purchase+tax $32,034
        purch = "$32034" if (yr == 2024 and trim == "SE") else ""
        fuel = "$3002" if purch else ""  # NPV from user's table (7-yr)
        rows.append(r(yr,"Toyota","Corolla Cross",f"{trim} Hybrid","Hybrid","1st Gen",adjusted,
            city=42,hwy=38,comb=42,mpg35="Yes",hp=196,awd="Yes",bat=1.3,
            pkg="TSS 2.0",nhtsa="5★",iihs="TSP",rp="4.0/5.0",
            cargo_r=24.3,cargo_max=46.0,tow=1500,gc=8.3,
            purch=purch,fuel15=fuel,
            qual="Yes",
            notes=("From prior research (ranked #1 in 7yr TCO); smaller than RAV4 " + suffix).strip()))

# ──────────────────────────────────────────────────────────────────────
# Write to file
# ──────────────────────────────────────────────────────────────────────
output_file = "/Users/jaz/development/car-comparison/car_comparison.csv"

with open(output_file, "a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=HEADERS)
    for row in rows:
        writer.writerow(row)

print(f"Appended {len(rows)} rows to {output_file}")
