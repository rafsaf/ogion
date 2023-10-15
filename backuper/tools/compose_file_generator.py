import yaml
from pathlib import Path
from endoflife_api import EOLApiProduct, EOL_DATA_DIR
from compose_db_models import ComposeFile
import json


for file in EOL_DATA_DIR.iterdir():
    with open(file, "r") as f:
        product = EOLApiProduct(cycles=json.load(f))

    valid_cycles = [cycle for cycle in product.cycles if cycle.valid]
    print(valid_cycles)
