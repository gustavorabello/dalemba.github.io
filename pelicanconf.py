from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

AUTHOR = "Gustavo R. Anjos"
SITENAME = "Misc Site"
SITESUBTITLE = "Tablaturas e receitas em um canto só."
SITEURL = ""

PATH = str(BASE_DIR / "content")
THEME = str(BASE_DIR / "theme")

TIMEZONE = "America/Sao_Paulo"
DEFAULT_LANG = "pt-br"

PAGE_PATHS = ["pages", "generated"]
ARTICLE_PATHS = []
STATIC_PATHS = ["static"]

PAGE_URL = "{slug}/index.html"
PAGE_SAVE_AS = "{slug}/index.html"

DIRECT_TEMPLATES = []
PAGINATED_TEMPLATES = {}
DEFAULT_PAGINATION = False

FEED_ALL_ATOM = None
FEED_ALL_RSS = None
CATEGORY_FEED_ATOM = None
CATEGORY_FEED_RSS = None
TAG_FEED_ATOM = None
TAG_FEED_RSS = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None
TRANSLATION_FEED_ATOM = None
TRANSLATION_FEED_RSS = None

USE_FOLDER_AS_CATEGORY = False
DELETE_OUTPUT_DIRECTORY = True
SLUGIFY_SOURCE = "basename"

MENUITEMS = [
    ("Home", "/"),
    ("Tablaturas", "/tablaturas/"),
    ("Receitas", "/receitas/"),
]
