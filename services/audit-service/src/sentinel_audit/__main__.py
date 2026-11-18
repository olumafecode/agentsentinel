"""Allow ``python -m sentinel_audit``."""

import sys

from sentinel_audit.cli import main

sys.exit(main())
