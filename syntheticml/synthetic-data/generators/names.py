"""Fictional name parts and a denylist of real brand/company names.

Names are fused from two invented stems (e.g. 'Kesarline') to reduce the chance
of matching a real business. The denylist test is a safety net, not a guarantee.
"""
import random

STEM_A = [
    "Aqua", "Arun", "Bodhi", "Chandra", "Dhara", "Eco", "Ganga", "Hira", "Indra", "Jala",
    "Kesar", "Kira", "Lumi", "Mithra", "Nila", "Nova", "Ojas", "Prana", "Pure", "Ritu",
    "Sama", "Suvarna", "Tara", "Udaya", "Vana", "Veda", "Vriksh", "Yuva", "Zara", "Saffra",
]
STEM_B = [
    "bloom", "brook", "crest", "dale", "field", "fizz", "glow", "grove", "haven", "kart",
    "leaf", "line", "loom", "mint", "nest", "pact", "path", "peak", "ray", "ridge",
    "root", "sprout", "stone", "shore", "vale", "vista", "wave", "well", "wick", "wing",
]

INDUSTRY_WORD = {
    "Beverages": ["Beverages", "Drinks"],
    "FMCG": ["Consumer Products", "Consumer Goods"],
    "Cosmetics": ["Cosmetics", "Beauty"],
    "Personal Care": ["Personal Care", "Hygiene Products"],
    "Food": ["Foods", "Food Products"],
    "Pharmaceuticals": ["Pharma", "Healthcare", "Life Sciences"],
    "Electronics": ["Electronics", "Devices"],
    "Appliances": ["Appliances", "Home Appliances"],
    "Automotive": ["Auto Components", "Automotive Parts"],
    "Retail": ["Retail", "Stores"],
    "E-commerce": ["Online Retail", "Digital Commerce"],
    "Household Products": ["Home Care", "Household Products"],
    "Industrial Goods": ["Industrial Products", "Engineering Goods"],
}
LEGAL_SUFFIX = ["Pvt Ltd", "Pvt Ltd", "Pvt Ltd", "Ltd", "LLP"]

SUPPLIER_WORD = {
    "PET bottle manufacturer": ["PET Bottles", "Preforms & Bottles"],
    "plastic resin supplier": ["Polymers", "Resins"],
    "flexible packaging supplier": ["Flexibles", "Flexi Pack"],
    "cap supplier": ["Caps", "Cap Works"],
    "closure supplier": ["Closures", "Closure Systems"],
    "label supplier": ["Labels", "Label Prints"],
    "shrink-film supplier": ["Shrink Films", "Polyfilms"],
    "pouch supplier": ["Pouches", "Pouch Pack"],
    "carton supplier": ["Cartons", "Corrugators"],
    "packaging converter": ["Converters", "Packaging Solutions"],
    "raw-material supplier": ["Raw Materials", "Polychem"],
    "component supplier": ["Pack Components", "Packaging Components"],
}
BUYER_WORD = {
    "distributor": ["Distributors", "Distribution"],
    "wholesaler": ["Wholesale Traders", "Wholesalers"],
    "retailer": ["Retail Mart", "General Stores"],
    "supermarket": ["Supermarket", "Hypermart"],
    "e-commerce seller": ["Online Sellers", "E-Store"],
    "institutional buyer": ["Hospitality Services", "Institutional Supplies"],
    "manufacturing customer": ["Manufacturing", "Industries"],
}
RECYCLER_WORD = ["Recyclers", "Polymer Recycling", "Reprocessors", "Waste Solutions", "Recovery Works"]

LOCALITY_A = ["Kesar", "Nilgiri", "Suryodaya", "Amrit", "Shanti", "Vasant", "Navrang", "Prabhat", "Sagar", "Mandar"]
LOCALITY_B = ["Industrial Area", "Udyog Nagar", "Business Park", "Trade Centre", "Commercial Complex", "Logistics Park"]

# Real brand / company names that generated names must never contain (case-insensitive, whole word or fused).
DENYLIST = [
    "amul", "bisleri", "britannia", "cocacola", "coca-cola", "coke", "colgate", "dabur", "dettol",
    "dove", "godrej", "haldiram", "himalaya", "hindustan unilever", "itc", "lifebuoy", "maggi",
    "marico", "nestle", "nivea", "parle", "patanjali", "pepsi", "reliance", "tata", "bajaj",
    "mahindra", "maruti", "samsung", "philips", "havells", "blue star", "voltas", "whirlpool",
    "flipkart", "amazon", "myntra", "meesho", "bigbasket", "dmart", "zepto", "blinkit", "swiggy",
    "cipla", "sun pharma", "dr reddy", "lupin", "emami", "wipro", "vicco", "kinley", "aquafina",
    "frooti", "thums up", "sprite", "fanta", "limca", "maaza", "paper boat", "lays", "kurkure",
    "bingo", "mamaearth", "lakme", "ponds", "vim", "surf", "rin", "ariel", "tide", "harpic", "lizol",
]


def fused(rng: random.Random) -> str:
    return rng.choice(STEM_A) + rng.choice(STEM_B)


def contains_denylisted(name: str) -> bool:
    low = name.lower()
    words = set(low.replace("-", " ").split())
    for bad in DENYLIST:
        if " " in bad or "-" in bad:
            if bad in low:
                return True
        elif bad in words:
            return True
    return False


def unique(rng: random.Random, used: set, make) -> str:
    for _ in range(500):
        name = make()
        if name not in used and not contains_denylisted(name):
            used.add(name)
            return name
    raise RuntimeError("could not generate a unique fictional name")


def company_name(rng, industry, used):
    return unique(rng, used, lambda: f"{fused(rng)} {rng.choice(INDUSTRY_WORD[industry])} {rng.choice(LEGAL_SUFFIX)}")


def supplier_name(rng, supplier_type, used):
    return unique(rng, used, lambda: f"{fused(rng)} {rng.choice(SUPPLIER_WORD[supplier_type])} Pvt Ltd")


def buyer_name(rng, buyer_type, used):
    suffix = "" if buyer_type == "retailer" else rng.choice([" Pvt Ltd", " LLP", ""])
    return unique(rng, used, lambda: f"{fused(rng)} {rng.choice(BUYER_WORD[buyer_type])}{suffix}")


def recycler_name(rng, used):
    return unique(rng, used, lambda: f"{fused(rng)} {rng.choice(RECYCLER_WORD)} Pvt Ltd")


def brand(rng, used):
    return unique(rng, used, lambda: fused(rng))


def locality(rng):
    return f"{rng.choice(LOCALITY_A)} {rng.choice(LOCALITY_B)}"
