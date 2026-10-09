"""States, GST state codes (verify before product use), cities and PIN prefixes.

Real state and city names are used only so that intra-/inter-state tax logic is
realistic. Street-level address parts are fictional (see names.py).
"""

# name: (gst_state_code, two-letter abbreviation, PIN first digit, cities)
STATES = {
    "Delhi": ("07", "DL", "1", ["New Delhi", "Delhi"]),
    "Haryana": ("06", "HR", "1", ["Gurugram", "Faridabad", "Sonipat", "Panipat"]),
    "Punjab": ("03", "PB", "1", ["Ludhiana", "Mohali", "Jalandhar"]),
    "Himachal Pradesh": ("02", "HP", "1", ["Baddi", "Solan"]),
    "Uttar Pradesh": ("09", "UP", "2", ["Noida", "Ghaziabad", "Lucknow", "Kanpur"]),
    "Uttarakhand": ("05", "UK", "2", ["Haridwar", "Rudrapur", "Dehradun"]),
    "Rajasthan": ("08", "RJ", "3", ["Jaipur", "Bhiwadi", "Jodhpur"]),
    "Gujarat": ("24", "GJ", "3", ["Ahmedabad", "Vadodara", "Surat", "Vapi"]),
    "Maharashtra": ("27", "MH", "4", ["Mumbai", "Pune", "Nagpur", "Aurangabad"]),
    "Goa": ("30", "GA", "4", ["Verna", "Margao"]),
    "Madhya Pradesh": ("23", "MP", "4", ["Indore", "Bhopal", "Pithampur"]),
    "Karnataka": ("29", "KA", "5", ["Bengaluru", "Mysuru", "Hubballi"]),
    "Telangana": ("36", "TS", "5", ["Hyderabad", "Medchal"]),
    "Andhra Pradesh": ("37", "AP", "5", ["Visakhapatnam", "Vijayawada", "Sri City"]),
    "Tamil Nadu": ("33", "TN", "6", ["Chennai", "Coimbatore", "Hosur"]),
    "Kerala": ("32", "KL", "6", ["Kochi", "Thiruvananthapuram"]),
    "West Bengal": ("19", "WB", "7", ["Kolkata", "Howrah", "Durgapur"]),
    "Odisha": ("21", "OD", "7", ["Bhubaneswar", "Cuttack"]),
    "Assam": ("18", "AS", "7", ["Guwahati"]),
    "Bihar": ("10", "BR", "8", ["Patna", "Hajipur"]),
}


def state_code(state: str) -> str:
    return STATES[state][0]


def state_abbrev(state: str) -> str:
    return STATES[state][1]


def pin_prefix(state: str) -> str:
    return STATES[state][2]


# Two-digit PIN prefixes by state (illustrative, region-consistent; DS-17).
PIN_PREFIXES = {
    "Delhi": ["11"], "Haryana": ["12", "13"], "Punjab": ["14", "15"], "Himachal Pradesh": ["17"],
    "Uttar Pradesh": ["20", "22", "25"], "Uttarakhand": ["24", "26"], "Rajasthan": ["30", "31", "34"],
    "Gujarat": ["36", "38", "39"], "Maharashtra": ["40", "41", "43", "44"], "Goa": ["40"],
    "Madhya Pradesh": ["45", "46", "47"], "Karnataka": ["56", "57", "58"], "Telangana": ["50"],
    "Andhra Pradesh": ["51", "52", "53"], "Tamil Nadu": ["60", "63", "64"], "Kerala": ["68", "69"],
    "West Bengal": ["70", "71", "73"], "Odisha": ["75", "76"], "Assam": ["78"], "Bihar": ["80", "84", "85"],
}


def pin_prefixes(state: str) -> list:
    return PIN_PREFIXES[state]


def cities(state: str) -> list:
    return STATES[state][3]
