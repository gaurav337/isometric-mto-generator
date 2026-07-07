import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

from app.config import get_settings, Settings

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "provider" in response.json()

def test_health_check_providers():
    # 1. Test Mock when no keys are set
    def override_settings_mock():
        return Settings(nvidia_api_key=None, gemini_api_key=None, openrouter_api_key=None)
    app.dependency_overrides[get_settings] = override_settings_mock
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["provider"] == "mock"

    # 2. Test NVIDIA when nvidia key is set
    def override_settings_nvidia():
        return Settings(nvidia_api_key="test_key", gemini_api_key=None, openrouter_api_key=None)
    app.dependency_overrides[get_settings] = override_settings_nvidia
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["provider"] == "nvidia"

    # 3. Test Gemini when gemini key is set (and no nvidia key)
    def override_settings_gemini():
        return Settings(nvidia_api_key=None, gemini_api_key="test_key", openrouter_api_key=None)
    app.dependency_overrides[get_settings] = override_settings_gemini
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["provider"] == "gemini"

    # 4. Test OpenRouter when openrouter key is set (and no other key)
    def override_settings_openrouter():
        return Settings(nvidia_api_key=None, gemini_api_key=None, openrouter_api_key="test_key")
    app.dependency_overrides[get_settings] = override_settings_openrouter
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["provider"] == "openrouter"

    # Clear overrides
    app.dependency_overrides.clear()

def test_upload_missing_file():
    response = client.post("/api/upload")
    assert response.status_code == 422

def test_upload_invalid_file_type():
    # Attempt to upload a text file — route returns 415 Unsupported Media Type
    response = client.post(
        "/api/upload",
        files={"file": ("test.txt", b"hello world", "text/plain")}
    )
    assert response.status_code == 415
    assert "Unsupported file type" in response.json()["detail"]

def test_get_mto_not_found():
    response = client.get("/api/mto/invalid-job-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_get_mto_csv_not_found():
    response = client.get("/api/mto/invalid-job-id/csv")
    assert response.status_code == 404

from unittest.mock import MagicMock, patch
from app.services.extractor import ExtractionError

def test_upload_fallback_to_mock():
    # Mock get_extractor to return a mock extractor that raises ExtractionError
    mock_extractor = MagicMock()
    mock_extractor.extract.side_effect = ExtractionError("API failure")
    mock_extractor.source = "nvidia"
    
    with open("test_image.png", "rb") as f:
        file_bytes = f.read()
        
    with patch("app.routes.mto.get_extractor", return_value=mock_extractor):
        response = client.post(
            "/api/upload",
            files={"file": ("test_image.png", file_bytes, "image/png")}
        )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert response.json()["status"] == "PENDING"
    
    # Retrieve job and verify source is mock (indicating fallback worked)
    get_response = client.get(f"/api/mto/{job_id}")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "COMPLETED"
    assert get_response.json()["source"] == "mock"
