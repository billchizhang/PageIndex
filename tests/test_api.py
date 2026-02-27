import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app import app, API_TOKEN
import os

client = TestClient(app)

def test_missing_api_key():
    response = client.post("/index-pdf")
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API Key"}

def test_wrong_api_key():
    response = client.post(
        "/index-pdf",
        headers={"X-API-Key": "completely-wrong-token"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API Key"}

def test_invalid_file_extension():
    # Make a dummy txt file
    with open("dummy.txt", "w") as f:
        f.write("This is a text file.")
    
    with open("dummy.txt", "rb") as f:
        response = client.post(
            "/index-pdf",
            headers={"X-API-Key": API_TOKEN},
            files={"file": ("dummy.txt", f, "text/plain")}
        )

    os.remove("dummy.txt")
    
    assert response.status_code == 400
    assert response.json() == {"detail": "File must be a PDF"}

@patch("app.page_index_main")
def test_valid_pdf_upload(mock_page_index_main):
    # Mock the return value of the PageIndex processor to avoid actual LLM calls
    mock_response = {"status": "success", "nodes": [{"id": 0, "text": "Mocked Content"}]}
    mock_page_index_main.return_value = mock_response

    # Create a dummy pdf
    with open("dummy.pdf", "wb") as f:
        f.write(b"%PDF-1.4\n%Dummy PDF content\n")
        
    with open("dummy.pdf", "rb") as f:
        response = client.post(
            "/index-pdf",
            headers={"X-API-Key": API_TOKEN},
            files={"file": ("dummy.pdf", f, "application/pdf")}
        )

    os.remove("dummy.pdf")

    assert response.status_code == 200
    assert response.json() == mock_response
    mock_page_index_main.assert_called_once()
    
    # Check that the tmp file was correctly passed and then cleaned up
    tmp_path_called = mock_page_index_main.call_args[0][0]
    assert tmp_path_called.startswith("/tmp/")
    assert tmp_path_called.endswith("dummy.pdf")
    assert not os.path.exists(tmp_path_called) # Cleaned up by the finally block


# ── /index-md tests ──────────────────────────────────────────────────

def test_invalid_md_file_extension():
    with open("dummy.txt", "w") as f:
        f.write("This is a text file.")

    with open("dummy.txt", "rb") as f:
        response = client.post(
            "/index-md",
            headers={"X-API-Key": API_TOKEN},
            files={"file": ("dummy.txt", f, "text/plain")},
        )

    os.remove("dummy.txt")

    assert response.status_code == 400
    assert response.json() == {"detail": "File must be a Markdown file"}


@patch("app.page_index_main")
def test_valid_md_upload(mock_page_index_main):
    mock_response = {"status": "success", "nodes": [{"id": 0, "text": "Mocked Content"}]}
    mock_page_index_main.return_value = mock_response

    with open("dummy.md", "w") as f:
        f.write("# Dummy MD content\n")

    with open("dummy.md", "rb") as f:
        response = client.post(
            "/index-md",
            headers={"X-API-Key": API_TOKEN},
            files={"file": ("dummy.md", f, "text/markdown")},
        )

    os.remove("dummy.md")

    assert response.status_code == 200
    assert response.json() == mock_response
    mock_page_index_main.assert_called_once()

    tmp_path_called = mock_page_index_main.call_args[0][0]
    assert tmp_path_called.startswith("/tmp/")
    assert tmp_path_called.endswith("dummy.md")
    assert not os.path.exists(tmp_path_called)


# ── /index-txt tests ─────────────────────────────────────────────────

def test_invalid_txt_file_extension():
    with open("dummy.pdf", "w") as f:
        f.write("This is a pdf file.")

    with open("dummy.pdf", "rb") as f:
        response = client.post(
            "/index-txt",
            headers={"X-API-Key": API_TOKEN},
            files={"file": ("dummy.pdf", f, "application/pdf")},
        )

    os.remove("dummy.pdf")

    assert response.status_code == 400
    assert response.json() == {"detail": "File must be a Text file"}


@patch("app.page_index_main")
def test_valid_txt_upload(mock_page_index_main):
    mock_response = {"status": "success", "nodes": [{"id": 0, "text": "Mocked Content"}]}
    mock_page_index_main.return_value = mock_response

    with open("dummy.txt", "w") as f:
        f.write("Dummy TXT content\n")

    with open("dummy.txt", "rb") as f:
        response = client.post(
            "/index-txt",
            headers={"X-API-Key": API_TOKEN},
            files={"file": ("dummy.txt", f, "text/plain")},
        )

    os.remove("dummy.txt")

    assert response.status_code == 200
    assert response.json() == mock_response
    mock_page_index_main.assert_called_once()

    tmp_path_called = mock_page_index_main.call_args[0][0]
    assert tmp_path_called.startswith("/tmp/")
    assert tmp_path_called.endswith("dummy.txt")
    assert not os.path.exists(tmp_path_called)
