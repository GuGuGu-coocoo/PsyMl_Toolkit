"""Installed-distribution smoke test used by CI."""

import json

import psyml
from psyml.protocol import capabilities_payload, schema_text

assert psyml.__version__ == "0.1.0"
assert capabilities_payload()["schema_version"] == "1.0"
assert json.loads(schema_text("analysis_config"))["title"] == "PsyML analysis configuration"
