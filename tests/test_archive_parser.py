from unittest.mock import MagicMock, patch
from src.archive_parser import unzip
import pytest


@patch("src.archive_parser.logger")
@patch("src.archive_parser.zipfile.ZipFile")
@patch("src.archive_parser.Path")
def test_unzip_directory_exists(mock_Path, mock_ZipFile, mock_logger):

    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_Path.return_value = mock_path_instance

    unzip(zip_path="test.zip", extract_to="test_dir")

    mock_path_instance.exists.assert_called_once()

    mock_ZipFile.assert_not_called()

    mock_logger.info.assert_called_with("File exists skipping Unzipping")

@patch("src.archive_parser.zipfile.is_zipfile")
@patch("src.archive_parser.Path")
def test_unzip_invalid_zipfile(mock_Path, mock_is_zipfile):

    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = False
    mock_Path.return_value = mock_path_instance
    zip_path = "not_a_zip.txt"
    mock_is_zipfile.return_value = False

    with pytest.raises(ValueError) as err:
        unzip(zip_path=zip_path, extract_to="tweet_data")

    assert f"{zip_path} is not a valid zip file" in str(err.value)
