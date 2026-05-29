from starlette import status

def test_health_root(client):
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}

def test_health_connections(client):
    response = client.get("/health/connections")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), dict)

def test_health_connections_has_db_tea_profiles_key(client):
    response = client.get("/health/connections")
    data = response.json()
    assert "db_tea_profiles" in data
