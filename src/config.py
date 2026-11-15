from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
HTML_CACHE = RAW / "html"
INTERIM = DATA / "interim"
OUTPUT = DATA / "output"

REFRESH = False
USER_AGENT = "NYU-student-research-bot (tl4732@nyu.edu)"
REQUEST_DELAY_SEC = 1.0
LLM_MODEL = "qwen2.5:7b"
MANHATTAN_ZIP_PREFIXES = ("100", "101", "102")