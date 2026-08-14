import io
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient


def test_upload_invalid_extension(client: TestClient):
    file_content = b"fake content"
    files = {"file": ("test.exe", io.BytesIO(file_content), "application/x-msdownload")}
    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 400
    err_msg = response.json().get("error", {}).get("message", "") or response.json().get("detail", "")
    assert "Unsupported file extension" in err_msg


def test_upload_empty_file(client: TestClient):
    files = {"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}
    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 400
    err_msg = response.json().get("error", {}).get("message", "") or response.json().get("detail", "")
    assert "Empty file" in err_msg


def test_upload_invalid_magic_bytes(client: TestClient):
    files = {"file": ("fake.jpg", io.BytesIO(b"this is plain text not a jpeg"), "image/jpeg")}
    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 400
    err_msg = response.json().get("error", {}).get("message", "") or response.json().get("detail", "")
    assert "File content does not match supported image or PDF formats" in err_msg


@patch("cloudinary.uploader.upload")
def test_upload_valid_jpeg_mocked(mock_upload: MagicMock, client: TestClient):
    mock_upload.return_value = {
        "secure_url": "https://res.cloudinary.com/demo/image/upload/v1234/test.jpg",
        "public_id": "foundation-erp/test",
        "format": "jpg",
        "bytes": 500,
        "resource_type": "image",
    }

    # Valid JPEG header: \xff\xd8\xff\xe0
    valid_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100
    files = {"file": ("photo.jpg", io.BytesIO(valid_jpeg), "image/jpeg")}
    response = client.post("/api/v1/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["secure_url"] == "https://res.cloudinary.com/demo/image/upload/v1234/test.jpg"
    assert data["public_id"] == "foundation-erp/test"
    assert data["format"] == "jpg"


@patch("cloudinary.uploader.upload")
def test_upload_base64_jpeg_mocked(mock_upload: MagicMock, client: TestClient):
    import base64
    mock_upload.return_value = {
        "secure_url": "https://res.cloudinary.com/demo/image/upload/v1234/base64_test.jpg",
        "public_id": "foundation-erp/base64_test",
        "format": "jpg",
        "bytes": 200,
        "resource_type": "image",
    }

    valid_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 50
    b64_str = "data:image/jpeg;base64," + base64.b64encode(valid_jpeg).decode("utf-8")

    response = client.post(
        "/api/v1/upload/base64",
        json={"data": b64_str, "folder": "member-requests"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["public_id"] == "foundation-erp/base64_test"


def get_token(client: TestClient, username: str = "superadmin") -> str:
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "TestPassword123!"},
    )
    return login_res.json()["access_token"]


@patch("cloudinary.uploader.destroy")
def test_delete_media_mocked(mock_destroy: MagicMock, client: TestClient):
    token = get_token(client, "superadmin")
    mock_destroy.return_value = {"result": "ok"}
    response = client.delete(
        "/api/v1/upload/foundation-erp/sample_photo",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["result"] == "ok"
