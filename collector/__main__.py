import logging

from .refresh import run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
run()
