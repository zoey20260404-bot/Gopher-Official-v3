"""健康检查接口集成测试。"""

from fastapi.testclient import TestClient

from gopher_agent.main import create_app


def test_health_returns_ok() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
