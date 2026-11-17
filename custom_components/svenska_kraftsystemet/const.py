"""Constants for Swedish Power System."""
from datetime import timedelta
DOMAIN = "svenska_kraftsystemet"
CONF_API_KEY = "api_key"
API_URL = "https://web-api.tp.entsoe.eu/api"
SCAN_INTERVAL = timedelta(minutes=60)
# EIC codes verified against previously successful ENTSO-E API requests.
AREAS = {
    "SE1": "10Y1001A1001A44P", "SE2": "10Y1001A1001A45N",
    "SE3": "10Y1001A1001A46L", "SE4": "10Y1001A1001A47J",
    "SE": "10YSE-1--------K",  # Sweden control-area code
    "FI": "10YFI-1--------U", "NO1": "10YNO-1--------2",
    "NO3": "10YNO-3--------J", "NO4": "10YNO-4--------9",
    "DK1": "10YDK-1--------W", "DK2": "10YDK-2--------M",
    "DE": "10Y1001A1001A82H", "PL": "10YPL-AREA-----S",
    "LT": "10YLT-1001A0008Q",
}
BORDERS = (
    ("SE1", "FI"), ("SE1", "NO4"), ("SE2", "NO3"),
    ("SE2", "NO4"), ("SE3", "NO1"), ("SE3", "FI"),
    ("SE3", "DK1"), ("SE4", "DK2"), ("SE4", "DE"),
    ("SE4", "PL"), ("SE4", "LT"),
)
PRODUCTION_TYPES = {
    "B01": "Biomass", "B02": "Lignite", "B03": "Coal-derived gas",
    "B04": "Natural gas", "B05": "Hard coal", "B06": "Oil", "B07": "Oil shale",
    "B08": "Peat", "B09": "Geothermal", "B10": "Pumped storage",
    "B11": "Run-of-river hydro", "B12": "Reservoir hydro", "B13": "Marine",
    "B14": "Nuclear", "B15": "Other renewable", "B16": "Solar",
    "B17": "Waste", "B18": "Offshore wind", "B19": "Onshore wind",
    "B20": "Other",
}
