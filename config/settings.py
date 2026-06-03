import os
from datetime import datetime


CATEGORIES: dict[str, dict] = {
    "https://mnsht.net/category/1":  {"name": "uae",      "label": "الإمارات",   "template_key": None,         "use_ai": True},
    "https://mnsht.net/category/20": {"name": "saudi",    "label": "السعودية",   "template_key": None,         "use_ai": True},
    "https://mnsht.net/category/21": {"name": "egypt",    "label": "مصر",        "template_key": None,         "use_ai": True},
    "https://mnsht.net/category/22": {"name": "gulf",     "label": "الخليج",     "template_key": None,         "use_ai": True},
    "https://mnsht.net/category/23": {"name": "arab",     "label": "عربي",       "template_key": None,         "use_ai": True},
    "https://mnsht.net/category/7":  {"name": "world",    "label": "العالم",     "template_key": None,         "use_ai": True},


    "https://mnsht.net/category/10": {"name": "economy",  "label": "الاقتصاد",   "template_key": "اقتصاد",    "use_ai": False},
    "https://mnsht.net/category/8":  {"name": "sports",   "label": "رياضة",      "template_key": "رياضة",     "use_ai": False},
    "https://mnsht.net/category/11": {"name": "arts",     "label": "فن",         "template_key": "فن",        "use_ai": False},
    "https://mnsht.net/category/13": {"name": "culture",  "label": "ثقافة",      "template_key": "ثقافة",     "use_ai": False},
    "https://mnsht.net/category/14": {"name": "cars",     "label": "سيارات",     "template_key": "سيارات",    "use_ai": False},
    "https://mnsht.net/category/15": {"name": "tech",     "label": "تكنولوجيا",  "template_key": "تكنولوجيا", "use_ai": False},
    "https://mnsht.net/category/16": {"name": "misc",     "label": "متنوع",      "template_key": "عام",       "use_ai": False},
}

AI_CATEGORY_URLS: set[str] = {url for url, cfg in CATEGORIES.items() if cfg["use_ai"]}

AI_TEMPLATE_MAP: dict[int, str] = {0: "عام", 1: "سياسة"}

SCRAPE_INTERVAL_SECONDS: int = 30
SCRAPE_TIMEOUT_CONNECT: int  = 8
SCRAPE_TIMEOUT_READ: int     = 25
SCRAPE_MAX_RETRIES: int      = 4
SCRAPE_RETRY_DELAY: int      = 3
MAX_SCRAPE_PAGES: int        = 3
PARALLEL_WORKERS: int        = len(CATEGORIES)


SCRAPE_ONLY_NEW: bool = True


ENABLE_FACEBOOK_POSTING: bool  = True
FACEBOOK_START_DATE            = datetime(2026, 5, 20)
FACEBOOK_END_DATE              = datetime(2026, 12, 31)
MAX_QUEUE_AGE_HOURS: float     = 3.0
AGING_MULTIPLIER: float        = 0.12

PUBLISH_LOG_RETENTION_DAYS: int = 30


PRIORITY_THRESHOLD_INSTAGRAM: int = 5
PRIORITY_THRESHOLD_TWITTER:   int = 1   
PRIORITY_THRESHOLD_FACEBOOK:  int = 5   


INSTAGRAM_MIN_INTERVAL_SECONDS: int = 30   # أقل حاجة آمنة
TWITTER_MIN_INTERVAL_SECONDS:   int = 15
FACEBOOK_MIN_INTERVAL_SECONDS:  int = 60

FACEBOOK_MAX_PER_HOUR:  int = 25
TWITTER_MAX_PER_HOUR:   int = 50
INSTAGRAM_MAX_PER_HOUR: int = 20   # الحد اليومي 25 post

BURST_WINDOW_SECONDS: int = 60
BURST_MAX_INSTANT:    int = 2
