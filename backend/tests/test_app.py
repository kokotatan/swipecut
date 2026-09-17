import io
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import main
from db import get_db
from models import Base


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    upload_dir = tmp_path / "original"
    segment_dir = tmp_path / "segments"
    export_dir = tmp_path / "export"
    for directory in (upload_dir, segment_dir, export_dir):
        directory.mkdir()

    monkeypatch.setattr(main, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(main, "SEGMENTS_DIR", str(segment_dir))
    monkeypatch.setattr(main, "EXPORT_DIR", str(export_dir))
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 20 * 1024 * 1024)

    def override_get_db():
        database = testing_session()
        try:
            yield database
        finally:
            database.close()

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client, tmp_path
    main.app.dependency_overrides.clear()
    engine.dispose()


def create_test_video(path: Path):
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=c=orange:s=320x240:d=6",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=880:duration=6",
                "-shortest",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(path),
                "-y",
            ],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        pytest.skip("ffmpeg is required for the integration test")


def test_health_and_input_validation(client):
    test_client, _ = client
    assert test_client.get("/health").json()["status"] == "healthy"

    response = test_client.post(
        "/api/upload",
        files={"file": ("notes.txt", b"not a video", "text/plain")},
    )
    assert response.status_code == 415
    assert test_client.get("/api/file/999999").status_code == 404


def test_video_workflow_from_upload_to_safe_zip(client):
    test_client, tmp_path = client
    source = tmp_path / "sample.mp4"
    create_test_video(source)

    with source.open("rb") as video:
        response = test_client.post(
            "/api/upload?chunk_sec=5",
            files={"file": ("../sample.mp4", video, "video/mp4")},
        )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["segments_count"] == 2

    first = test_client.get(
        "/api/next_segment", params={"video_id": result["video_id"]}
    ).json()
    assert first["url"] == f"/api/file/{first['segment_id']}"
    assert test_client.get(first["url"]).status_code == 200

    assert test_client.post(
        "/api/name", params={"segment_id": first["segment_id"], "name": "../best clip"}
    ).status_code == 200
    assert test_client.post(
        "/api/decide", params={"segment_id": first["segment_id"], "decision": "keep"}
    ).status_code == 200

    second = test_client.get(
        "/api/next_segment", params={"video_id": result["video_id"]}
    ).json()
    assert test_client.post(
        "/api/decide", params={"segment_id": second["segment_id"], "decision": "drop"}
    ).status_code == 200

    progress = test_client.get(
        "/api/progress", params={"video_id": result["video_id"]}
    ).json()
    assert progress == {"total": 2, "kept": 1, "dropped": 1, "pending": 0}

    archive_response = test_client.get(
        "/api/export_zip", params={"video_id": result["video_id"]}
    )
    assert archive_response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(archive_response.content)) as archive:
        names = archive.namelist()
    assert names == ["best clip.mp4"]
    assert all("/" not in name and "\\" not in name and ".." not in name for name in names)
