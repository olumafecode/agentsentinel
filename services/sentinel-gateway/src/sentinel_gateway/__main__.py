"""Allow ``python -m sentinel_gateway``."""

import sys

from sentinel_gateway.cli import main

sys.exit(main())
