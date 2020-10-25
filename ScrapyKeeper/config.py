# Statement for enabling the development environment
import os

DEBUG = True

# Define the application directory


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_CONNECTION_STRING', None)
SQLALCHEMY_TRACK_MODIFICATIONS = False
DATABASE_CONNECT_OPTIONS = {}

# Application threads. A common general assumption is
# using 2 per available processor cores - to handle
# incoming requests using one and performing background
# operations using the other.
THREADS_PER_PAGE = 2

# Enable protection agains *Cross-site Request Forgery (CSRF)*
CSRF_ENABLED = True

# Use a secure, unique and absolutely secret key for
# signing the data.
CSRF_SESSION_KEY = "secret"

# Secret key for signing cookies
SECRET_KEY = "secret"

# log
LOG_LEVEL = 'INFO'

AWS_DEFAULT_REGION = 'eu-west-1'
DEFAULT_CLUSTER_NAME = 'crawler'

# spider services
SERVER_TYPE = 'scrapyd'

servers_string = os.getenv('SERVERS', '')
SERVERS = [s.strip() for s in servers_string.split(',') if s]

# basic auth
NO_AUTH = False
BASIC_AUTH_USERNAME = 'admin'
BASIC_AUTH_PASSWORD = 'admin'
BASIC_AUTH_FORCE = True

NO_SENTRY = False
SENTRY_URI = os.getenv('SENTRY_URI', None)

# http settings

DEFAULT_TIMEOUT = 30  # seconds

SPIDERS_SYNC_INTERVAL_IN_SECONDS = int(os.getenv('SPIDERS_SYNC_INTERVAL_IN_SECONDS', 120))

BACK_IN_TIME_ENABLED = bool(int(os.getenv('BACK_IN_TIME_ENABLED', 1)))

AUTO_SCHEDULE_ENABLED = bool(int(os.getenv('AUTO_SCHEDULE_ENABLED', 1)))
AUTO_SCHEDULE_DEFAULT_VALUE = bool(int(os.getenv('AUTO_SCHEDULE_DEFAULT_VALUE', 1)))

MIN_LOAD_RATIO_MULTIPLIER = float(os.getenv('MIN_LOAD_RATIO_MULTIPLIER', 0.5))
MAX_LOAD_RATIO_MULTIPLIER = float(os.getenv('MAX_LOAD_RATIO_MULTIPLIER', 6))
MAX_SPIDERS_START_AT_ONCE = int(os.getenv('MAX_SPIDERS_START_AT_ONCE', 10))
MAX_LOAD_ALLOWED = int(os.getenv('MAX_LOAD_ALLOWED', 250))
DEFAULT_AUTOTHROTTLE_MAX_CONCURRENCY = int(os.getenv('AUTOTHROTTLE_MAX_CONCURRENCY', 10))

USED_MEMORY_PERCENT_THRESHOLD = int(os.getenv('USED_MEMORY_PERCENT_THRESHOLD', 90))  # the threshold for launching new spiders
RUNS_IN_CLOUD = bool(int(os.getenv('RUNS_IN_CLOUD', 1)))
