import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXAMPLES = ROOT / "examples"


@pytest.fixture(scope="session", autouse=True)
def _isolate_logs(tmp_path_factory):
    """LoggerService writes to relative logs/ paths; keep them out of the repo."""
    old = os.getcwd()
    os.chdir(tmp_path_factory.mktemp("cwd"))
    yield
    os.chdir(old)


@pytest.fixture
def valid_csv_text():
    return (EXAMPLES / "sample_valid_data.csv").read_text()


@pytest.fixture
def error_csv_text():
    return (EXAMPLES / "sample_error_data.csv").read_text()
