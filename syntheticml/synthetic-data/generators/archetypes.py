"""Industry → product archetypes → packaging components.

ALL weights, recycled-content ranges and HSN headings are ILLUSTRATIVE
engineering assumptions (docs/generator-assumptions.md), not market data.
Category is declared by component form (docs/plastic-category-mapping.md, DS-09).
"""

# form → (synthetic_category, category_confidence, illustrative HSN, preferred supplier types)
# synthetic_category is a MODELLING CONVENTION (DS-09), not a legal classification.
FORM_RULES = {
    "bottle": ("CAT_I", "declared", "3923", ["PET bottle manufacturer", "packaging converter"]),
    "jar": ("CAT_I", "declared", "3923", ["PET bottle manufacturer", "packaging converter"]),
    "cap": ("CAT_I", "declared", "3923", ["cap supplier", "closure supplier", "component supplier"]),
    "closure": ("CAT_I", "declared", "3923", ["closure supplier", "cap supplier"]),
    "tray": ("CAT_I", "declared", "3923", ["component supplier", "packaging converter"]),
    "drum": ("CAT_I", "declared", "3923", ["component supplier", "packaging converter"]),
    "pail": ("CAT_I", "declared", "3923", ["component supplier", "packaging converter"]),
    "tub": ("CAT_I", "declared", "3923", ["packaging converter"]),
    "eps_block": ("CAT_I", "declared", "3921", ["component supplier", "packaging converter"]),
    "blister": ("CAT_I", "ambiguous", "3920", ["packaging converter"]),
    "film": ("CAT_II", "declared", "3920", ["shrink-film supplier", "flexible packaging supplier"]),
    "shrink_wrap": ("CAT_II", "declared", "3920", ["shrink-film supplier"]),
    "stretch_wrap": ("CAT_II", "declared", "3920", ["shrink-film supplier"]),
    "label_film": ("CAT_II", "declared", "3919", ["label supplier"]),
    "bag": ("CAT_II", "declared", "3923", ["flexible packaging supplier"]),
    "mailer": ("CAT_II", "declared", "3923", ["flexible packaging supplier"]),
    "liner": ("CAT_II", "declared", "3923", ["flexible packaging supplier", "shrink-film supplier"]),
    "pouch_mono": ("CAT_II", "declared", "3923", ["pouch supplier", "flexible packaging supplier"]),
    "sachet_mono": ("CAT_II", "declared", "3923", ["pouch supplier", "flexible packaging supplier"]),
    "pouch_laminate": ("CAT_III", "declared", "3923", ["pouch supplier", "flexible packaging supplier", "packaging converter"]),
    "sachet_laminate": ("CAT_III", "declared", "3923", ["pouch supplier", "flexible packaging supplier", "packaging converter"]),
    "laminated_tube": ("CAT_III", "declared", "3923", ["packaging converter"]),
    "compostable_bag": ("CAT_IV", "declared", "3923", ["flexible packaging supplier", "pouch supplier"]),
    "compostable_mailer": ("CAT_IV", "declared", "3923", ["flexible packaging supplier"]),
    "carton": ("NA", "declared", "4819", ["carton supplier"]),
    "box": ("NA", "declared", "4819", ["carton supplier"]),
    "paper_label": ("NA", "declared", "4821", ["label supplier"]),
    "void_fill": ("NA", "declared", "4808", ["carton supplier"]),
    "glass_bottle": ("NA", "declared", "7010", ["component supplier"]),
    "can": ("NA", "declared", "7612", ["component supplier"]),
}

PLASTIC_MATERIALS = {"PET", "HDPE", "LDPE", "LLDPE", "PP", "PVC", "PS", "MLP", "COMPOSTABLE"}

# Supplier type → materials it can sensibly supply (resin / raw-material suppliers sell polymer,
# not finished packaging components, so they own no component forms).
SUPPLIER_TYPE_MATERIALS = {
    "PET bottle manufacturer": ["PET"],
    "plastic resin supplier": ["PET", "HDPE", "LDPE", "LLDPE", "PP"],
    "flexible packaging supplier": ["LDPE", "LLDPE", "MLP", "COMPOSTABLE"],
    "cap supplier": ["PP", "HDPE"],
    "closure supplier": ["PP", "HDPE"],
    "label supplier": ["PP", "PAPER", "PVC"],
    "shrink-film supplier": ["LDPE", "LLDPE", "PP", "PVC"],
    "pouch supplier": ["LDPE", "LLDPE", "MLP", "COMPOSTABLE"],
    "carton supplier": ["CARDBOARD", "PAPER"],
    "packaging converter": ["PET", "HDPE", "PP", "PS", "PVC", "MLP"],
    "raw-material supplier": ["PS", "PVC", "HDPE", "PP"],
    "component supplier": ["PS", "PP", "HDPE", "METAL", "GLASS"],
}
# Supplier type → component forms it supplies (derived from FORM_RULES).
SUPPLIER_TYPE_FORMS = {t: sorted(f for f, rule in FORM_RULES.items() if t in rule[3]) for t in SUPPLIER_TYPE_MATERIALS}
SUPPLIER_TYPE_UNIT = {
    "PET bottle manufacturer": "pcs", "plastic resin supplier": "MT", "flexible packaging supplier": "kg",
    "cap supplier": "pcs", "closure supplier": "pcs", "label supplier": "rolls", "shrink-film supplier": "kg",
    "pouch supplier": "pcs", "carton supplier": "pcs", "packaging converter": "kg",
    "raw-material supplier": "MT", "component supplier": "pcs",
}


def C(name, form, material, w, rc=(0, 0)):
    """component spec: name, form, material, weight range g, recycled-content range %"""
    return {"name": name, "form": form, "material": material, "weight_g": w, "recycled_pct": rc}


CARTON = C("Outer carton (per-unit share)", "carton", "CARDBOARD", (8, 30), (30, 80))

# industry → list of archetypes
ARCHETYPES = {
    "Beverages": [
        {"category": "Carbonated soft drink", "unit": "bottle", "case": [12, 24],
         "desc": ["Cola", "Lemon Twist", "Orange Burst", "Cream Soda", "Jeera Fizz"], "size": ["300 ml", "500 ml", "750 ml", "1.25 L"],
         "parts": [C("PET bottle", "bottle", "PET", (18, 40), (0, 30)), C("Cap", "cap", "PP", (1.8, 2.6)),
                   C("Label", "label_film", "PP", (0.5, 1.3)), CARTON]},
        {"category": "Packaged drinking water", "unit": "bottle", "case": [12, 24],
         "desc": ["Drinking Water", "Mineral Water"], "size": ["500 ml", "1 L", "2 L"],
         "parts": [C("PET bottle", "bottle", "PET", (14, 32), (0, 20)), C("Cap", "cap", "HDPE", (1.5, 2.2)),
                   C("Label", "label_film", "PP", (0.4, 1.0)), C("Shrink wrap (per-unit share)", "shrink_wrap", "LDPE", (2, 5))]},
        {"category": "Glass bottled drink", "unit": "bottle", "case": [24],
         "desc": ["Ginger Ale", "Club Soda", "Tonic Water"], "size": ["200 ml", "300 ml"],
         "parts": [C("Glass bottle", "glass_bottle", "GLASS", (170, 260)), C("Crown cap", "cap", "METAL", (2, 3)),
                   C("Paper label", "paper_label", "PAPER", (0.6, 1.2)), CARTON]},
        {"category": "Flavoured water", "unit": "bottle", "case": [12, 24],
         "desc": ["Lemon Water", "Mint Water", "Cucumber Water"], "size": ["500 ml", "750 ml"],
         "parts": [C("PET bottle", "bottle", "PET", (16, 30), (0, 25)), C("Cap", "cap", "PP", (1.6, 2.4)),
                   C("Shrink sleeve", "shrink_wrap", "PVC", (1.5, 3)), CARTON]},
        {"category": "Juice bottle", "unit": "bottle", "case": [12, 24],
         "desc": ["Orange Juice", "Mixed Fruit Juice", "Pomegranate Juice"], "size": ["200 ml", "1 L"],
         "parts": [C("HDPE bottle", "bottle", "HDPE", (18, 40)), C("Cap", "cap", "PP", (2, 3.5)),
                   C("Label", "label_film", "PP", (0.5, 1.2)), CARTON]},
        {"category": "Fruit drink (pouch)", "unit": "pouch", "case": [24, 48],
         "desc": ["Mango Drink", "Guava Nectar"], "size": ["160 ml", "200 ml"],
         "parts": [C("Spouted laminate pouch", "pouch_laminate", "MLP", (4, 8)), CARTON]},
    ],
    "FMCG": [
        {"category": "Detergent powder", "unit": "pack", "case": [12, 24],
         "desc": ["Detergent Powder", "Washing Powder"], "size": ["500 g", "1 kg"],
         "parts": [C("LLDPE pouch", "pouch_mono", "LLDPE", (6, 14)), CARTON]},
        {"category": "Shampoo sachet", "unit": "sachet", "case": [144, 288],
         "desc": ["Herbal Shampoo Sachet", "Anti-dandruff Sachet"], "size": ["6 ml", "8 ml"],
         "parts": [C("Laminate sachet", "sachet_laminate", "MLP", (0.4, 0.9))]},
        {"category": "Toothpaste", "unit": "tube", "case": [24, 48],
         "desc": ["Herbal Toothpaste", "Clove Gel"], "size": ["100 g", "150 g"],
         "parts": [C("Laminated tube", "laminated_tube", "MLP", (5, 9)), C("Flip cap", "cap", "PP", (2, 4)),
                   C("Mono carton", "box", "CARDBOARD", (8, 14), (30, 70))]},
    ],
    "Food": [
        {"category": "Savoury snacks", "unit": "pack", "case": [24, 48],
         "desc": ["Masala Chips", "Salted Crisps", "Spicy Bhujia"], "size": ["52 g", "75 g", "150 g"],
         "parts": [C("Laminate snack pouch", "pouch_laminate", "MLP", (3, 9)), CARTON]},
        {"category": "Biscuits", "unit": "pack", "case": [24, 48],
         "desc": ["Butter Cookies", "Glucose Biscuits"], "size": ["100 g", "200 g"],
         "parts": [C("BOPP wrapper", "film", "PP", (1.5, 4)), C("Inner tray", "tray", "PS", (3, 7)), CARTON]},
        {"category": "Edible oil", "unit": "bottle", "case": [12, 16],
         "desc": ["Groundnut Oil", "Mustard Oil"], "size": ["1 L", "2 L"],
         "parts": [C("PET jar", "jar", "PET", (30, 55), (0, 10)), C("Cap", "cap", "HDPE", (3, 5)), CARTON]},
    ],
    "Personal Care": [
        {"category": "Shampoo", "unit": "bottle", "case": [24, 36],
         "desc": ["Shampoo", "Conditioner"], "size": ["180 ml", "340 ml"],
         "parts": [C("HDPE bottle", "bottle", "HDPE", (20, 42), (0, 25)), C("Flip cap", "cap", "PP", (3, 6)),
                   C("Label", "label_film", "PP", (0.6, 1.4))]},
        {"category": "Body lotion", "unit": "bottle", "case": [24],
         "desc": ["Body Lotion", "Aloe Gel"], "size": ["200 ml", "400 ml"],
         "parts": [C("HDPE bottle", "bottle", "HDPE", (22, 45)), C("Pump closure", "closure", "PP", (6, 11)), CARTON]},
    ],
    "Cosmetics": [
        {"category": "Face cream", "unit": "jar", "case": [24, 48],
         "desc": ["Day Cream", "Night Repair Cream"], "size": ["50 g", "100 g"],
         "parts": [C("PP jar", "jar", "PP", (12, 22)), C("Lid", "cap", "PP", (4, 7)), C("Mono carton", "box", "CARDBOARD", (6, 12))]},
        {"category": "Face wash", "unit": "tube", "case": [48],
         "desc": ["Face Wash", "Foaming Cleanser"], "size": ["50 ml", "100 ml"],
         "parts": [C("Laminated tube", "laminated_tube", "MLP", (4, 8)), C("Flip cap", "cap", "PP", (2, 4))]},
    ],
    "Pharmaceuticals": [
        {"category": "Tablets (strip)", "unit": "strip", "case": [100, 200],
         "desc": ["Paracetamol-type Tablets (synthetic SKU)", "Antacid Tablets (synthetic SKU)"], "size": ["10 tabs", "15 tabs"],
         "parts": [C("PVC blister", "blister", "PVC", (1.2, 2.5)), C("Mono carton", "box", "CARDBOARD", (3, 6))]},
        {"category": "Syrup", "unit": "bottle", "case": [48],
         "desc": ["Cough Syrup (synthetic SKU)", "Tonic (synthetic SKU)"], "size": ["100 ml", "200 ml"],
         "parts": [C("PET bottle", "bottle", "PET", (14, 24)), C("Cap", "cap", "PP", (2, 4)), C("Mono carton", "box", "CARDBOARD", (6, 10))]},
        {"category": "Capsules bottle", "unit": "bottle", "case": [48],
         "desc": ["Multivitamin Capsules (synthetic SKU)"], "size": ["30 caps", "60 caps"],
         "parts": [C("HDPE bottle", "bottle", "HDPE", (12, 20)), C("Cap", "cap", "PP", (3, 5))]},
    ],
    "Electronics": [
        {"category": "Bluetooth speaker", "unit": "unit", "case": [4, 10],
         "desc": ["Bluetooth Speaker", "Soundbar Mini"], "size": ["5 W", "10 W"],
         "parts": [C("EPS insert", "eps_block", "PS", (25, 80)), C("Protective bag", "bag", "LDPE", (4, 12)),
                   C("Product box", "box", "CARDBOARD", (120, 300))]},
        {"category": "Power bank", "unit": "unit", "case": [10, 20],
         "desc": ["Power Bank", "Slim Power Bank"], "size": ["10000 mAh", "20000 mAh"],
         "parts": [C("PET clamshell", "tray", "PET", (15, 35)), C("Product box", "box", "CARDBOARD", (40, 90))]},
    ],
    "_electronics_more": [
        {"category": "Wall charger", "unit": "unit", "case": [20, 50],
         "desc": ["Wall Charger", "Dual-port Charger"], "size": ["20 W", "33 W"],
         "parts": [C("PP inner tray", "tray", "PP", (6, 14)), C("Protective bag", "bag", "LDPE", (2, 5)),
                   C("Product box", "box", "CARDBOARD", (35, 70))]},
        {"category": "Mobile accessory", "unit": "unit", "case": [50, 100],
         "desc": ["USB-C Cable", "Earphones", "Phone Case"], "size": ["1 m", "Standard"],
         "parts": [C("PET blister clamshell", "tray", "PET", (8, 18)), C("Paper backing card", "box", "CARDBOARD", (10, 25))]},
    ],
    "Appliances": [
        {"category": "Mixer grinder", "unit": "unit", "case": [1, 2],
         "desc": ["Mixer Grinder", "Hand Blender"], "size": ["500 W", "750 W"],
         "parts": [C("EPS blocks", "eps_block", "PS", (120, 300)), C("LDPE cover", "bag", "LDPE", (15, 40)),
                   C("Corrugated box", "box", "CARDBOARD", (400, 900))]},
        {"category": "Table fan", "unit": "unit", "case": [1, 2],
         "desc": ["Table Fan", "Wall Fan"], "size": ["400 mm"],
         "parts": [C("EPS blocks", "eps_block", "PS", (80, 200)), C("Corrugated box", "box", "CARDBOARD", (350, 700))]},
    ],
    "Automotive": [
        {"category": "Auto filter", "unit": "unit", "case": [10, 20],
         "desc": ["Oil Filter", "Air Filter"], "size": ["Type A", "Type B"],
         "parts": [C("LDPE bag", "bag", "LDPE", (3, 8)), C("Mono carton", "box", "CARDBOARD", (40, 90))]},
        {"category": "Brake pads", "unit": "set", "case": [10],
         "desc": ["Brake Pad Set"], "size": ["Front", "Rear"],
         "parts": [C("PP tray", "tray", "PP", (20, 40)), C("Stretch wrap (per-unit share)", "stretch_wrap", "LLDPE", (3, 8)),
                   C("Mono carton", "box", "CARDBOARD", (50, 100))]},
    ],
    "Retail": [
        {"category": "Store-brand staples", "unit": "pack", "case": [20, 40],
         "desc": ["Basmati Rice", "Toor Dal", "Sugar"], "size": ["1 kg", "5 kg"],
         "parts": [C("LDPE pouch", "pouch_mono", "LDPE", (8, 30))]},
        {"category": "Carry bags", "unit": "bag", "case": [500],
         "desc": ["Store Carry Bag"], "size": ["Medium", "Large"],
         "parts": [C("Carry bag", "bag", "LDPE", (6, 14))]},
        {"category": "Compostable carry bags", "unit": "bag", "case": [500],
         "desc": ["Compostable Carry Bag"], "size": ["Medium"],
         "parts": [C("Compostable carry bag", "compostable_bag", "COMPOSTABLE", (6, 12))]},
    ],
    "E-commerce": [
        {"category": "Courier shipment", "unit": "shipment", "case": [100],
         "desc": ["Standard Courier Pack", "Express Courier Pack"], "size": ["Small", "Medium", "Large"],
         "parts": [C("Courier mailer", "mailer", "LDPE", (12, 40))]},
        {"category": "Boxed shipment", "unit": "shipment", "case": [50],
         "desc": ["Boxed Shipment"], "size": ["Medium", "Large"],
         "parts": [C("Shipping box", "box", "CARDBOARD", (150, 400), (40, 90)), C("Air cushion film", "film", "LDPE", (4, 12)),
                   C("Paper void fill", "void_fill", "PAPER", (10, 40))]},
        {"category": "Eco shipment", "unit": "shipment", "case": [100],
         "desc": ["Eco Mailer Pack"], "size": ["Small", "Medium"],
         "parts": [C("Compostable mailer", "compostable_mailer", "COMPOSTABLE", (15, 35))]},
    ],
    "Household Products": [
        {"category": "Floor cleaner", "unit": "bottle", "case": [12, 24],
         "desc": ["Floor Cleaner", "Toilet Cleaner"], "size": ["500 ml", "1 L"],
         "parts": [C("HDPE bottle", "bottle", "HDPE", (35, 60), (0, 30)), C("Cap", "cap", "PP", (3, 6)),
                   C("Label", "label_film", "PP", (0.8, 1.6))]},
        {"category": "Dishwash refill", "unit": "pouch", "case": [24],
         "desc": ["Dishwash Liquid Refill"], "size": ["500 ml", "1 L"],
         "parts": [C("LLDPE refill pouch", "pouch_mono", "LLDPE", (6, 12))]},
        {"category": "Air freshener", "unit": "can", "case": [24],
         "desc": ["Room Freshener"], "size": ["220 ml"],
         "parts": [C("Aluminium can", "can", "METAL", (30, 45)), C("Actuator cap", "cap", "PP", (5, 9))]},
    ],
    "Industrial Goods": [
        {"category": "Adhesive", "unit": "drum", "case": [1],
         "desc": ["Industrial Adhesive"], "size": ["20 kg", "50 kg"],
         "parts": [C("HDPE drum", "drum", "HDPE", (900, 2200))]},
        {"category": "Fasteners", "unit": "box", "case": [20],
         "desc": ["Hex Bolts", "Anchor Fasteners"], "size": ["100 pcs"],
         "parts": [C("LDPE bag", "bag", "LDPE", (5, 12)), C("Carton", "box", "CARDBOARD", (60, 120))]},
        {"category": "Coatings", "unit": "pail", "case": [1],
         "desc": ["Floor Coating"], "size": ["10 L", "20 L"],
         "parts": [C("HDPE pail", "pail", "HDPE", (500, 1100)), C("Stretch wrap (per-unit share)", "stretch_wrap", "LLDPE", (10, 30))]},
    ],
}

ARCHETYPES["Electronics"] = ARCHETYPES["Electronics"] + ARCHETYPES.pop("_electronics_more")

# Illustrative finished-goods price ranges (₹ per selling unit) — NOT market data.
UNIT_PRICE = {
    "Beverages": (25, 60), "FMCG": (10, 150), "Food": (10, 100), "Personal Care": (60, 300),
    "Cosmetics": (150, 800), "Pharmaceuticals": (30, 300), "Electronics": (800, 20000),
    "Appliances": (1500, 40000), "Automotive": (200, 5000), "Retail": (50, 1000),
    "E-commerce": (200, 2000), "Household Products": (40, 300), "Industrial Goods": (500, 20000),
}
