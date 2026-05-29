from unittest.mock import MagicMock, patch
from src.archive_parser import unzip
import pytest

@patch("src.archive_parser.zipfile.is_Zipfile")
@patch("src.archive_parser.zipfile.is_Zipfile")
def test_unzip():
    pass