async def test_rate_limit_429(async_client, rate_limited):
    res = await async_client.get("/v1/cars/")
    assert res.status_code == 429
    assert "Превышено количество запросов" in res.json()["detail"]
