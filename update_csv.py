#!/usr/bin/env python3
import csv
import re

GAS_PRICE = 4.40
ELEC_RATE = 0.21

def parse_price(val):
    if not val or str(val).strip() in ('', 'TBD'):
        return None
    cleaned = str(val).replace('$', '').replace(',', '').strip()
    try:
        return float(cleaned)
    except:
        return None

def fmt(val):
    if val is None:
        return ''
    return f"${int(round(val)):,}"

def mpg_comb(city, hwy):
    try:
        c, h = float(city), float(hwy)
        if c > 0 and h > 0:
            return 2*c*h/(c+h)
    except:
        pass
    return None

def fuel_gas(city, hwy):
    c = mpg_comb(city, hwy)
    if c:
        return round(GAS_PRICE / c, 3)
    return None

# ---------------------------------------------------------------------------
# TBD MSRP estimates for 2026 Forester Gas
TBD_MSRP = {
    (2026,'Subaru','Forester','Base'): 31500,
    (2026,'Subaru','Forester','Premium'): 34500,
    (2026,'Subaru','Forester','Sport'): 36500,
    (2026,'Subaru','Forester','Limited'): 39500,
    (2026,'Subaru','Forester','Touring'): 43500,
    (2026,'Subaru','Forester','Wilderness'): 38500,
}

# ---------------------------------------------------------------------------
# USED PRICES (25K miles, Pittsburgh market)
# For 2025-2026: use MSRP (handled in code)
UP = {}

# Toyota RAV4 Gas
for yr,trim,price in [
    (2018,'LE',14500),(2018,'XLE',15500),(2018,'SE',17000),(2018,'Limited',18500),(2018,'Platinum',20000),
    (2019,'LE',17000),(2019,'XLE',18500),(2019,'XLE Premium',20000),(2019,'Adventure',20500),(2019,'Limited',22500),
    (2020,'LE',19500),(2020,'XLE',21000),(2020,'XLE Premium',22500),(2020,'Adventure',23000),(2020,'TRD Off-Road',23000),(2020,'Limited',24500),
    (2021,'LE',22000),(2021,'XLE',23500),(2021,'XLE Premium',25500),(2021,'Adventure',26000),(2021,'TRD Off-Road',26000),(2021,'Limited',27500),
    (2022,'LE',24500),(2022,'XLE',26000),(2022,'XLE Premium',28000),(2022,'Adventure',29000),(2022,'TRD Off-Road',29000),(2022,'Limited',31000),
    (2023,'LE',26500),(2023,'XLE',28500),(2023,'XLE Premium',30500),(2023,'Adventure',31500),(2023,'TRD Off-Road',31500),(2023,'Limited',33500),
    (2024,'LE',28500),(2024,'XLE',30500),(2024,'XLE Premium',32500),(2024,'Adventure',34000),(2024,'TRD Off-Road',34000),(2024,'Limited',36500),
]:
    UP[(yr,'Toyota','RAV4',trim)] = price

# Toyota RAV4 Hybrid
for yr,trim,price in [
    (2019,'LE',22500),(2019,'XLE',24000),(2019,'XLE Premium',26500),(2019,'SE',26000),(2019,'Limited',28500),
    (2020,'LE',25500),(2020,'XLE',27500),(2020,'XLE Premium',30000),(2020,'SE',29500),(2020,'Limited',32000),
    (2021,'LE',27500),(2021,'XLE',30000),(2021,'XLE Premium',33000),(2021,'SE',32000),(2021,'Limited',35500),
    (2022,'LE',30000),(2022,'XLE',32500),(2022,'XLE Premium',35500),(2022,'SE',35000),(2022,'Limited',38000),
    (2023,'LE',31000),(2023,'XLE',33500),(2023,'XLE Premium',36500),(2023,'SE',36000),(2023,'Limited',39500),
    (2024,'LE',33000),(2024,'XLE',36000),(2024,'XLE Premium',39000),(2024,'SE',38000),(2024,'Limited',42000),
]:
    UP[(yr,'Toyota','RAV4 Hybrid',trim)] = price

# Toyota RAV4 Prime
for yr,trim,price in [
    (2021,'SE',31000),(2021,'XSE',33000),(2021,'XSE Technology',36000),
    (2022,'SE',33000),(2022,'XSE',36000),(2022,'XSE Technology',39500),
    (2023,'SE',35500),(2023,'XSE',39000),(2023,'XSE Technology',42500),
    (2024,'SE',38000),(2024,'XSE',41500),(2024,'XSE Technology',45000),
]:
    UP[(yr,'Toyota','RAV4 Prime',trim)] = price

# Toyota Venza
for yr,trim,price in [
    (2021,'LE',25500),(2021,'XLE',28000),(2021,'XSE',30000),(2021,'Limited',32500),
    (2022,'LE',27000),(2022,'XLE',29500),(2022,'XSE',31500),(2022,'Limited',34000),
    (2023,'LE',28000),(2023,'XLE',30500),(2023,'XSE',32500),(2023,'Limited',35500),
    (2024,'LE',30000),(2024,'XLE',33000),(2024,'XSE',35000),(2024,'Limited',38000),
]:
    UP[(yr,'Toyota','Venza',trim)] = price

# Toyota C-HR (25K-mile premium over typical ~60K mileage, discontinued model)
for yr,trim,price in [
    (2018,'LE',13500),(2018,'XLE',14500),(2018,'XLE Premium',15500),(2018,'Limited',17000),
    (2019,'LE',14500),(2019,'XLE',16000),(2019,'XLE Premium',17000),(2019,'Limited',18500),
    (2020,'LE',16000),(2020,'XLE',17500),(2020,'Nightshade',18000),(2020,'Limited',19500),
    (2021,'LE',19500),(2021,'XLE',21000),(2021,'Nightshade',21500),(2021,'Limited',23000),
    (2022,'LE',21000),(2022,'XLE',22500),(2022,'Nightshade',23000),(2022,'Limited',24500),
]:
    UP[(yr,'Toyota','C-HR',trim)] = price

# Toyota Corolla Cross Gas
for yr,trim,price in [
    (2022,'L',16500),(2022,'LE',18500),(2022,'XSE',20500),
    (2023,'L',18000),(2023,'LE',20000),(2023,'XSE',22500),
    (2024,'L',20000),(2024,'LE',22500),(2024,'XSE',25000),
]:
    UP[(yr,'Toyota','Corolla Cross',trim)] = price

# Toyota Corolla Cross Hybrid
for yr,trim,price in [
    (2024,'S Hybrid',26000),(2024,'SE Hybrid',27500),(2024,'XSE Hybrid',29000),
]:
    UP[(yr,'Toyota','Corolla Cross',trim)] = price

# Subaru Forester 4th Gen
for yr,trim,price in [
    (2018,'2.5i',11000),(2018,'2.5i Premium',13000),(2018,'2.5i Sport',14000),(2018,'2.5i Limited',16500),(2018,'2.5i Touring',19000),
    (2018,'2.0XT Premium',14000),(2018,'2.0XT Touring',17000),
]:
    UP[(yr,'Subaru','Forester',trim)] = price

# Subaru Forester 5th Gen
for yr,trim,price in [
    (2019,'Base',14500),(2019,'Premium',16500),(2019,'Sport',17500),(2019,'Limited',19500),(2019,'Touring',22000),
    (2020,'Base',16000),(2020,'Premium',18000),(2020,'Sport',19500),(2020,'Limited',22000),(2020,'Touring',24500),
    (2021,'Base',18000),(2021,'Premium',20000),(2021,'Sport',22000),(2021,'Limited',24500),(2021,'Touring',27000),
    (2022,'Base',22500),(2022,'Premium',24500),(2022,'Sport',26500),(2022,'Limited',29000),(2022,'Touring',32000),(2022,'Wilderness',27500),
    (2023,'Base',25000),(2023,'Premium',27500),(2023,'Sport',29500),(2023,'Limited',32000),(2023,'Touring',35500),(2023,'Wilderness',30500),
    (2024,'Base',26500),(2024,'Premium',29000),(2024,'Sport',31000),(2024,'Limited',33500),(2024,'Touring',37000),(2024,'Wilderness',32000),
]:
    UP[(yr,'Subaru','Forester',trim)] = price

# Honda CR-V Gas (KBB-researched, Pittsburgh, 25K miles)
for yr,trim,price in [
    (2018,'LX',18500),(2018,'EX',19500),(2018,'EX-L',20500),(2018,'Touring',22000),
    (2019,'LX',19500),(2019,'EX',20500),(2019,'EX-L',21500),(2019,'Touring',23000),
    (2020,'LX',20500),(2020,'EX',21500),(2020,'EX-L',23000),(2020,'Touring',25000),
    (2021,'LX',21500),(2021,'EX',23000),(2021,'EX-L',24000),(2021,'Touring',26500),
    (2022,'LX',22000),(2022,'EX',23500),(2022,'EX-L',25000),(2022,'Touring',27500),
    (2023,'LX',25000),(2023,'EX',26000),(2023,'EX-L',27500),(2023,'Sport',28000),(2023,'Sport-L',29000),(2023,'Sport Touring',29000),
    (2024,'LX',27000),(2024,'EX',28000),(2024,'EX-L',30000),(2024,'Sport',27500),(2024,'Sport-L',29000),(2024,'Sport Touring',30500),
]:
    UP[(yr,'Honda','CR-V',trim)] = price

# Honda CR-V Hybrid (KBB-researched, Pittsburgh, 25K miles)
for yr,trim,price in [
    (2020,'EX Hybrid',24000),(2020,'EX-L Hybrid',23500),(2020,'Touring Hybrid',25500),
    (2021,'EX Hybrid',24500),(2021,'EX-L Hybrid',25500),(2021,'Touring Hybrid',27000),
    (2022,'EX Hybrid',27000),(2022,'EX-L Hybrid',27500),(2022,'Touring Hybrid',28500),
    (2023,'EX-L Hybrid',29000),(2023,'Sport-L Hybrid',30000),(2023,'Sport Touring Hybrid',31000),
    (2024,'EX-L Hybrid',30500),(2024,'Sport-L Hybrid',31500),(2024,'Sport Touring Hybrid',33000),
]:
    UP[(yr,'Honda','CR-V',trim)] = price

# Ford Escape 3rd Gen Gas (2018-2019) — KBB-researched
for yr,trim,price in [
    (2018,'S',11000),(2018,'SE',12000),(2018,'SEL',12500),(2018,'Titanium',14000),
    (2019,'S',11500),(2019,'SE',13000),(2019,'SEL',14500),(2019,'Titanium',16000),
]:
    UP[(yr,'Ford','Escape',trim)] = price

# Ford Escape 4th Gen Gas (2020-2022) — KBB-researched
for yr,trim,price in [
    (2020,'S',13000),(2020,'SE',14000),(2020,'SE Sport',14500),(2020,'SEL',15500),(2020,'Titanium',17500),
    (2021,'S',15500),(2021,'SE',16000),(2021,'SE Sport',16500),(2021,'SEL',17500),(2021,'Titanium',18500),
    (2022,'S',15500),(2022,'SE',17000),(2022,'SE Sport',17500),(2022,'SEL',19500),(2022,'Titanium',22000),
]:
    UP[(yr,'Ford','Escape',trim)] = price

# Ford Escape Gas (2023-2024) — KBB-researched
for yr,trim,price in [
    (2023,'SE',18000),(2023,'ST-Line',19000),(2023,'SEL',21000),(2023,'Titanium',22500),
    (2024,'SE',19500),(2024,'ST-Line',21500),(2024,'SEL',23500),(2024,'Titanium',25500),
]:
    UP[(yr,'Ford','Escape',trim)] = price

# Ford Escape Hybrid — KBB-researched
for yr,trim,price in [
    (2020,'SE Hybrid',15000),(2020,'SEL Hybrid',16000),(2020,'Titanium Hybrid',16000),
    (2021,'SE Hybrid',16500),(2021,'SEL Hybrid',17500),(2021,'Titanium Hybrid',19500),
    (2022,'SE Hybrid',17500),(2022,'SEL Hybrid',19500),(2022,'Titanium Hybrid',21000),
    (2023,'SE Hybrid',18000),(2023,'SEL Hybrid',21000),(2023,'Titanium Hybrid',23500),
    (2024,'SE Hybrid',20500),(2024,'SEL Hybrid',22500),(2024,'Titanium Hybrid',25000),
]:
    UP[(yr,'Ford','Escape',trim)] = price

# Ford Escape PHEV — KBB-researched
for yr,trim,price in [
    (2020,'Titanium PHEV',18500),(2021,'Titanium PHEV',20000),(2022,'Titanium PHEV',21000),
]:
    UP[(yr,'Ford','Escape',trim)] = price

# Mazda CX-5 (KBB-researched, Pittsburgh, 25K miles)
for yr,trim,price in [
    (2018,'Sport',15500),(2018,'Touring',16000),(2018,'Grand Touring',17000),(2018,'Grand Touring Reserve',18000),(2018,'Signature',18500),
    (2019,'Sport',16500),(2019,'Touring',17500),(2019,'Grand Touring',17500),(2019,'Grand Touring Reserve',18500),(2019,'Signature',19500),
    (2020,'Sport',18500),(2020,'Touring',18000),(2020,'Grand Touring',18500),(2020,'Grand Touring Reserve',19000),(2020,'Signature',22000),
    (2021,'Sport',18000),(2021,'Touring',18500),(2021,'Carbon Edition',19500),(2021,'Grand Touring',19000),(2021,'Grand Touring Reserve',21500),(2021,'Signature',22000),
    (2022,'Sport',19500),(2022,'Touring',20500),(2022,'Carbon Edition',21500),(2022,'Grand Touring',22000),(2022,'Grand Touring Reserve',23000),(2022,'Signature',26500),
    (2023,'2.5 S',21000),(2023,'2.5 Select',22000),(2023,'2.5 Preferred',23200),(2023,'2.5 Preferred Plus',24000),
    (2023,'2.5 S Carbon Edition',22500),(2023,'2.5 GT',24000),(2023,'2.5 Turbo',25000),(2023,'2.5 Turbo Signature',26500),
    (2024,'2.5 S',21500),(2024,'2.5 Select',23000),(2024,'2.5 Preferred',24500),(2024,'2.5 Preferred Plus',25500),
    (2024,'2.5 S Carbon Edition',23500),(2024,'2.5 GT',26000),(2024,'2.5 Turbo',27000),(2024,'2.5 Turbo Signature',29000),
]:
    UP[(yr,'Mazda','CX-5',trim)] = price

# Hyundai Tucson 4th Gen Gas (2018-2021) — KBB-researched
for yr,trim,price in [
    (2018,'SE',13500),(2018,'Value',14000),(2018,'SEL',14000),(2018,'Sport',14500),(2018,'Night',15000),(2018,'Ultimate',15500),
    (2019,'SE',15000),(2019,'Value',15000),(2019,'SEL',15500),(2019,'Sport',16500),(2019,'Night',19000),(2019,'Ultimate',17500),
    (2020,'SE',15500),(2020,'Value',16000),(2020,'SEL',16500),(2020,'Sport',17000),(2020,'Night',17500),(2020,'Ultimate',19000),
    (2021,'SE',17000),(2021,'Value',17000),(2021,'SEL',18000),(2021,'Sport',18500),(2021,'Night',19000),(2021,'Ultimate',20000),
]:
    UP[(yr,'Hyundai','Tucson',trim)] = price

# Hyundai Tucson 5th Gen Gas (2022-2024) — KBB-researched
for yr,trim,price in [
    (2022,'SE',19000),(2022,'SEL',21000),(2022,'N Line',21500),(2022,'SEL Convenience',21500),(2022,'XRT',22000),(2022,'Limited',23000),
    (2023,'SE',21000),(2023,'SEL',22000),(2023,'N Line',23000),(2023,'SEL Convenience',23000),(2023,'XRT',23500),(2023,'Limited',24500),
    (2024,'SE',20500),(2024,'SEL',22000),(2024,'N Line',23000),(2024,'SEL Convenience',24000),(2024,'XRT',24000),(2024,'Limited',26000),
]:
    UP[(yr,'Hyundai','Tucson',trim)] = price

# Hyundai Tucson Hybrid — KBB-researched
for yr,trim,price in [
    (2022,'Blue Hybrid',21000),(2022,'SEL Hybrid',21500),(2022,'SEL Convenience Hybrid',20500),(2022,'N Line Hybrid',22500),(2022,'Limited Hybrid',24000),
    (2023,'Blue Hybrid',23000),(2023,'SEL Hybrid',24000),(2023,'SEL Convenience Hybrid',25000),(2023,'N Line Hybrid',25000),(2023,'Limited Hybrid',27000),
    (2024,'Blue Hybrid',24500),(2024,'SEL Hybrid',25000),(2024,'SEL Convenience Hybrid',26000),(2024,'N Line Hybrid',26500),(2024,'Limited Hybrid',28500),
]:
    UP[(yr,'Hyundai','Tucson',trim)] = price

# Hyundai Tucson PHEV — KBB-researched
for yr,trim,price in [
    (2022,'SEL PHEV',22000),(2022,'Limited PHEV',26000),
    (2023,'SEL PHEV',26000),(2023,'Limited PHEV',28000),
    (2024,'SEL PHEV',26000),(2024,'Limited PHEV',29000),
]:
    UP[(yr,'Hyundai','Tucson',trim)] = price

# Kia Sportage 4th Gen (2018-2022) — KBB-researched
for yr,trim,price in [
    (2018,'LX',12500),(2018,'S',13000),(2018,'EX',14000),(2018,'SX',15000),(2018,'SX Turbo',16000),
    (2019,'LX',13500),(2019,'S',14500),(2019,'EX',15500),(2019,'SX',16500),(2019,'SX Turbo',17500),
    (2020,'LX',15000),(2020,'S',16000),(2020,'EX',17000),(2020,'SX',18000),(2020,'SX Turbo',20000),
    (2021,'LX',16000),(2021,'S',17000),(2021,'EX',18000),(2021,'SX',19000),(2021,'SX Turbo',20500),
    (2022,'LX',16500),(2022,'S',17000),(2022,'EX',18500),(2022,'SX',20000),(2022,'SX Turbo',22000),
]:
    UP[(yr,'Kia','Sportage',trim)] = price

# Kia Sportage 5th Gen Gas (2023-2024) — KBB-researched
for yr,trim,price in [
    (2023,'LX',20000),(2023,'S',22000),(2023,'EX',23000),(2023,'X-Pro',24000),(2023,'SX Prestige',26500),
    (2024,'LX',21000),(2024,'S',22500),(2024,'EX',24500),(2024,'X-Pro',25500),(2024,'SX Prestige',29000),
]:
    UP[(yr,'Kia','Sportage',trim)] = price

# Kia Sportage Hybrid — KBB-researched
for yr,trim,price in [
    (2023,'LX Hybrid',22000),(2023,'EX Hybrid',25000),(2023,'SX Prestige Hybrid',28200),
    (2024,'LX Hybrid',23000),(2024,'EX Hybrid',25500),(2024,'SX Prestige Hybrid',29500),
]:
    UP[(yr,'Kia','Sportage',trim)] = price

# ---------------------------------------------------------------------------
# MPG corrections: key=(year,make,model,trim) -> (city,hwy) or special string
MPG_FIXES = {}

# 2025 RAV4 Gas
for trim in ['LE','XLE','XLE Premium','Adventure','TRD Off-Road','Limited']:
    MPG_FIXES[(2025,'Toyota','RAV4',trim)] = (27,33)

# 2025 RAV4 Hybrid
for trim in ['LE','XLE','XLE Premium','SE','Limited']:
    MPG_FIXES[(2025,'Toyota','RAV4 Hybrid',trim)] = (41,38)

# 2025 RAV4 Prime (fill with same display values as 2021-2024)
for trim in ['SE','XSE','XSE Technology']:
    MPG_FIXES[(2025,'Toyota','RAV4 Prime',trim)] = (42,'94 MPGe')

# 2026 RAV4 Prime
for trim in ['SE','XSE']:
    MPG_FIXES[(2026,'Toyota','RAV4 Prime',trim)] = (52,'107 MPGe')

# 2026 RAV4 Hybrid - correct AWD values (LE/SE=46/39, XLE Premium=45/38, Limited stays 43/37)
MPG_FIXES[(2026,'Toyota','RAV4 Hybrid','LE')] = (46,39)
MPG_FIXES[(2026,'Toyota','RAV4 Hybrid','XLE Premium')] = (45,38)
MPG_FIXES[(2026,'Toyota','RAV4 Hybrid','SE')] = (46,39)
# Limited already correct at 43/37

# 2023-2026 Ford Escape Gas (1.5T, FWD primary)
for trim in ['SE','ST-Line','SEL','Titanium']:
    MPG_FIXES[(2023,'Ford','Escape',trim)] = (27,34)
    MPG_FIXES[(2024,'Ford','Escape',trim)] = (27,33)
    MPG_FIXES[(2025,'Ford','Escape',trim)] = (27,34)
    MPG_FIXES[(2026,'Ford','Escape',trim)] = (27,34)

# 2025-2026 Forester 6th Gen Gas
for trim in ['Base','Premium']:
    MPG_FIXES[(2025,'Subaru','Forester',trim)] = (26,33)
    MPG_FIXES[(2026,'Subaru','Forester',trim)] = (26,33)
for trim in ['Sport','Touring','Limited']:
    MPG_FIXES[(2025,'Subaru','Forester',trim)] = (25,32)
    MPG_FIXES[(2026,'Subaru','Forester',trim)] = (25,32)
MPG_FIXES[(2025,'Subaru','Forester','Wilderness')] = (25,28)
MPG_FIXES[(2026,'Subaru','Forester','Wilderness')] = (24,28)

# ---------------------------------------------------------------------------
# CARGO corrections for 2025-2026 Forester 6th Gen Gas
CARGO_FIXES = {}
# Base/Wilderness: no panoramic moonroof -> 29.6/74.4
# Premium/Sport/Limited/Touring: with panoramic -> 27.5/69.1
for yr in [2025,2026]:
    for trim in ['Base','Wilderness']:
        CARGO_FIXES[(yr,'Subaru','Forester',trim)] = (29.6, 74.4)
    for trim in ['Premium','Sport','Limited','Touring']:
        CARGO_FIXES[(yr,'Subaru','Forester',trim)] = (27.5, 69.1)

# 2023-2026 Ford Escape Hybrid (missing cargo)
for yr in [2023,2024,2025,2026]:
    for trim in ['SE Hybrid','SEL Hybrid','Titanium Hybrid']:
        CARGO_FIXES[(yr,'Ford','Escape',trim)] = (37.5, 65.4)

# ---------------------------------------------------------------------------
# MAINTENANCE 7YR (Pittsburgh, total cost of ownership)
def age_multiplier(year):
    """Scale maintenance cost by vehicle age at purchase (2026 = purchase year).
    Low-mileage cars still age by calendar: seals, coolant, hoses, etc.
    Older cars also exit any remaining warranty sooner and reach high repair-prone ages."""
    age = 2026 - year
    return {0: 1.00, 1: 1.05, 2: 1.12, 3: 1.20, 4: 1.30,
            5: 1.42, 6: 1.55, 7: 1.68, 8: 1.80}.get(age, 1.00)

def get_maintenance(make, model, powertrain, gen, year):
    p = powertrain.upper()
    m = model.lower()
    if make == 'Toyota':
        if 'C-HR' in model:           return 4500
        if 'Corolla Cross' in model:
            return 4300 if 'hybrid' in p else 4600
        if 'Venza' in model:          return 4900
        if 'RAV4 Prime' in model:     return 5100
        if 'RAV4 Hybrid' in model:    return 5000
        if 'RAV4' in model:           return 5200
    if make == 'Subaru':
        if 'hybrid' in p.lower():     return 7000
        if '4th' in gen:              return 6200
        if '6th' in gen:              return 6800
        return 6500  # 5th gen
    if make == 'Honda':
        return 5000 if 'hybrid' in p.lower() else 5200
    if make == 'Ford':
        if 'phev' in p.lower():       return 8200
        if 'hybrid' in p.lower():     return 8000
        if '3rd' in gen:              return 9000
        return 8500
    if make == 'Mazda':
        return 5500 if ('turbo' in p.lower() or '2.5t' in p.lower()) else 4800
    if make == 'Hyundai':
        if 'phev' in p.lower():       return 6700
        if 'hybrid' in p.lower():     return 6500
        if '4th' in gen:              return 7200
        return 6800
    if make == 'Kia':
        if 'hybrid' in p.lower():     return 6200
        if '4th' in gen:              return 7000
        return 6500
    return 6000

# ---------------------------------------------------------------------------
# INSURANCE ANNUAL (Pittsburgh, 2 drivers, age 30, clean, excellent credit)
def get_insurance(make, model, powertrain, msrp):
    if msrp is None:
        msrp = 32000
    # Base by MSRP tier
    if msrp < 25000:      base = 2200
    elif msrp < 30000:    base = 2350
    elif msrp < 35000:    base = 2500
    elif msrp < 40000:    base = 2650
    elif msrp < 45000:    base = 2800
    elif msrp < 50000:    base = 2950
    else:                  base = 3100
    # Brand/powertrain adjustments
    adj = 0
    if make in ('Toyota','Mazda'):   adj -= 100
    if make == 'Honda':              adj -= 75
    if make == 'Ford':               adj += 150
    if make == 'Hyundai':            adj += 50
    if make == 'Kia':                adj += 100
    p = powertrain.lower()
    if 'phev' in p:                  adj += 100
    return int(round((base + adj) / 50.0) * 50)

# ---------------------------------------------------------------------------
# RESALE 7YR
# Retention factor (annual) by brand/powertrain, then * 0.88 Pittsburgh salt
RETENTION = {
    ('Toyota','gas'):       0.93,
    ('Toyota','hybrid'):    0.935,
    ('Toyota','phev'):      0.93,
    ('Toyota','chr'):       0.89,
    ('Toyota','ccross'):    0.91,
    ('Subaru','gas'):       0.91,
    ('Subaru','hybrid'):    0.905,
    ('Honda','gas'):        0.93,
    ('Honda','hybrid'):     0.935,
    ('Ford','gas'):         0.89,
    ('Ford','hybrid'):      0.895,
    ('Ford','phev'):        0.89,
    ('Mazda','gas'):        0.93,
    ('Mazda','turbo'):      0.92,
    ('Hyundai','4thgen'):   0.89,
    ('Hyundai','gas'):      0.90,
    ('Hyundai','hybrid'):   0.905,
    ('Hyundai','phev'):     0.90,
    ('Kia','4thgen'):       0.89,
    ('Kia','gas'):          0.90,
    ('Kia','hybrid'):       0.905,
}
PITTSBURGH = 0.88

def get_resale(make, model, powertrain, gen, purchase_price):
    if purchase_price is None:
        return None
    p = powertrain.lower()
    key = None
    if make == 'Toyota':
        if 'C-HR' in model:           key = ('Toyota','chr')
        elif 'Corolla Cross' in model: key = ('Toyota','ccross')
        elif 'hybrid' in p:           key = ('Toyota','hybrid')
        elif 'phev' in p:             key = ('Toyota','phev')
        else:                          key = ('Toyota','gas')
    elif make == 'Subaru':
        key = ('Subaru','hybrid') if 'hybrid' in p else ('Subaru','gas')
    elif make == 'Honda':
        key = ('Honda','hybrid') if 'hybrid' in p else ('Honda','gas')
    elif make == 'Ford':
        if 'phev' in p:    key = ('Ford','phev')
        elif 'hybrid' in p: key = ('Ford','hybrid')
        else:               key = ('Ford','gas')
    elif make == 'Mazda':
        key = ('Mazda','turbo') if ('turbo' in p.lower() or '2.5t' in p.lower()) else ('Mazda','gas')
    elif make == 'Hyundai':
        if '4th' in gen:    key = ('Hyundai','4thgen')
        elif 'phev' in p:   key = ('Hyundai','phev')
        elif 'hybrid' in p: key = ('Hyundai','hybrid')
        else:               key = ('Hyundai','gas')
    elif make == 'Kia':
        if '4th' in gen:    key = ('Kia','4thgen')
        elif 'hybrid' in p: key = ('Kia','hybrid')
        else:               key = ('Kia','gas')
    r = RETENTION.get(key, 0.91)
    factor = (r ** 7) * PITTSBURGH
    return int(round(purchase_price * factor / 500.0) * 500)

# ---------------------------------------------------------------------------
# PHEV gas-only MPG (city, hwy) for blended calculation
PHEV_GAS_MPG = {
    # (make, model_key): (city, hwy)
    'RAV4 Prime':       (38, 35),   # gas-only city/hwy
    'RAV4 Prime 2026':  (44, 38),
    'Escape PHEV':      (41, 34),   # FWD only gas mode
    'Tucson PHEV':      (35, 38),
}
# PHEV MPGe (city, hwy) for electric portion
PHEV_MPGE = {
    'RAV4 Prime':       (84, 83),   # EPA MPGe city/hwy
    'RAV4 Prime 2026':  (107, 107),
    'Escape PHEV':      (100, 84),  # stored in file
    'Tucson PHEV':      (80, 76),   # stored in file
}

def get_fuel_costs(make, model, powertrain, city_raw, hwy_raw, year):
    """Return (city_cost_per_mile, hwy_cost_per_mile)."""
    p = powertrain.lower()
    if 'phev' in p:
        if 'RAV4 Prime' in model:
            key = 'RAV4 Prime 2026' if year == 2026 else 'RAV4 Prime'
        elif make == 'Ford':
            key = 'Escape PHEV'
        elif make == 'Hyundai':
            key = 'Tucson PHEV'
        else:
            return None, None
        mpge_c, mpge_h = PHEV_MPGE[key]
        gas_c, gas_h   = PHEV_GAS_MPG[key]
        city = round(0.75*(33.7*ELEC_RATE/mpge_c) + 0.25*(GAS_PRICE/gas_c), 3)
        hwy  = round(0.75*(33.7*ELEC_RATE/mpge_h) + 0.25*(GAS_PRICE/gas_h), 3)
        return city, hwy
    # Gas or Hybrid: simple GAS_PRICE / MPG
    try:
        city_mpg = float(str(city_raw).replace(' MPGe','').strip())
        hwy_mpg  = float(str(hwy_raw).replace(' MPGe','').strip())
        return round(GAS_PRICE/city_mpg, 3), round(GAS_PRICE/hwy_mpg, 3)
    except:
        return None, None

# ---------------------------------------------------------------------------
# MAIN PROCESSING
input_file = '/Users/jaz/development/car-comparison/Car Comparison - Sheet1.csv'
output_file = '/Users/jaz/development/car-comparison/Car Comparison - Sheet1 Updated.csv'

with open(input_file, 'r', newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

header = rows[0]
data_rows = rows[1:]

# Find column indices
cols = {name: i for i, name in enumerate(header)}
print("Columns:", cols)

# Build new header (remove Battery_Reserve, split fuel cost into city+hwy)
new_header = []
battery_idx = None
fuel_idx = None
for i, col in enumerate(header):
    if col == 'Battery_Reserve':
        battery_idx = i
        continue
    if col in ('Fuel_per_year', 'Fuel_cost_per_mile'):
        new_header.append('Fuel_cost_city_per_mile')
        new_header.append('Fuel_cost_hwy_per_mile')
        fuel_idx = i
    else:
        new_header.append(col)

print(f"Battery_Reserve col: {battery_idx}, Fuel col: {fuel_idx}")

new_data = []
for row in data_rows:
    if not any(row):
        continue
    # Extend row if needed
    while len(row) < len(header):
        row.append('')

    year   = int(row[cols['Year']]) if row[cols['Year']].strip().isdigit() else 0
    make   = row[cols['Make']].strip()
    model  = row[cols['Model']].strip()
    trim   = row[cols['Trim']].strip()
    pwr    = row[cols['Powertrain']].strip()
    gen    = row[cols['Generation']].strip()
    msrp_raw = row[cols['MSRP_New_Est']].strip()

    # Parse MSRP
    msrp = parse_price(msrp_raw)
    if msrp is None:
        msrp = TBD_MSRP.get((year, make, model, trim))

    # ---- USED PRICE ----
    if year >= 2025:
        used_price = msrp
    else:
        used_price = UP.get((year, make, model, trim))

    # ---- MPG ----
    city_raw = row[cols['MPG_City']].strip()
    hwy_raw  = row[cols['MPG_Hwy']].strip()

    fix = MPG_FIXES.get((year, make, model, trim))
    if fix:
        city_raw = str(fix[0])
        hwy_raw  = str(fix[1])
    # else keep existing

    # ---- CARGO ----
    cargo_rear_raw = row[cols['Cargo_2nd_Row_cuft']].strip()
    cargo_max_raw  = row[cols['Max_Cargo_cuft']].strip()
    cargo_fix = CARGO_FIXES.get((year, make, model, trim))
    if cargo_fix:
        cargo_rear_raw = str(cargo_fix[0])
        cargo_max_raw  = str(cargo_fix[1])

    # ---- FUEL COST PER MILE (city + hwy separately) ----
    fuel_city, fuel_hwy = get_fuel_costs(make, model, pwr, city_raw, hwy_raw, year)

    # ---- MAINTENANCE ----
    maint = round(get_maintenance(make, model, pwr, gen, year) * age_multiplier(year) / 100) * 100

    # ---- INSURANCE ----
    ins = get_insurance(make, model, pwr, msrp)

    # ---- RESALE ----
    purchase_price = used_price if year < 2025 else msrp
    resale = get_resale(make, model, pwr, gen, purchase_price)

    # Build new row (skip Battery_Reserve)
    new_row = []
    for i, val in enumerate(row):
        if i == battery_idx:
            continue
        elif i == cols['MSRP_New_Est']:
            new_row.append(fmt(msrp) if (not val.strip() or val.strip()=='TBD') and msrp else val)
        elif i == cols['Used_Price_Est_25K_mi']:
            new_row.append(fmt(used_price) if used_price else '')
        elif i == cols['MPG_City']:
            new_row.append(city_raw)
        elif i == cols['MPG_Hwy']:
            new_row.append(hwy_raw)
        elif i == cols['Cargo_2nd_Row_cuft']:
            new_row.append(cargo_rear_raw)
        elif i == cols['Max_Cargo_cuft']:
            new_row.append(cargo_max_raw)
        elif i == fuel_idx:
            new_row.append(str(fuel_city) if fuel_city else '')
            new_row.append(str(fuel_hwy) if fuel_hwy else '')
        elif i == cols['Maintenance_7yr']:
            new_row.append(fmt(maint))
        elif i == cols['Insurance_Annual']:
            new_row.append(fmt(ins))
        elif i == cols['Resale_7yr']:
            new_row.append(fmt(resale) if resale else '')
        else:
            new_row.append(val)

    new_data.append(new_row)

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(new_header)
    writer.writerows(new_data)

print(f"Done! Written to: {output_file}")
print(f"Rows processed: {len(new_data)}")

# Quick spot-check
print("\nSpot checks:")
for row in new_data[:3]:
    print(row[:10])
