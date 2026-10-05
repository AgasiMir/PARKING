from unittest.mock import patch

from app.domains.v1.cars.schemas import (
    CarParkingAndPriceSchema,
    CarParkSchema,
    ParkingPriceTimeCursorSchema,
    ParkingReadSchema,
)
from app.errors.python_exceptions import CarIsNotParkedException, CarNotFoundException


async def test_get_parking_empty_list(async_client):
    res = await async_client.get("/v1/cars/")
    assert res.status_code == 200
    assert isinstance(ParkingPriceTimeCursorSchema(**res.json()), ParkingPriceTimeCursorSchema)
    assert res.json()["parking_and_price_data"] == []
    assert res.json()["has_more"] is False
    assert res.json()["next_cursor"] is None


async def test_get_parkings(async_client):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    park = await async_client.post("/v1/cars/park/", json=park_car.model_dump())
    assert park.status_code == 201

    res = await async_client.get("/v1/cars/")
    assert res.status_code == 200
    assert isinstance(ParkingPriceTimeCursorSchema(**res.json()), ParkingPriceTimeCursorSchema)


async def test_get_parking_list_with_two_parkings(async_client):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    park = await async_client.post("/v1/cars/park/", json=park_car.model_dump())
    assert park.status_code == 201

    park_car_2 = CarParkSchema(mark="Toyota", model="Camry", number="us12kff", color="red")
    park_2 = await async_client.post("/v1/cars/park/", json=park_car_2.model_dump())
    assert park_2.status_code == 201

    res = await async_client.get("/v1/cars/", params={"limit": 1})
    assert res.status_code == 200

    # первая страница
    assert isinstance(ParkingPriceTimeCursorSchema(**res.json()), ParkingPriceTimeCursorSchema)
    assert res.json()["parking_and_price_data"][0]["parking_data"]["number"] == "us12kff"
    assert res.json()["has_more"] is True
    assert res.json()["next_cursor"] is not None

    # вторая страница
    last_id = res.json()["next_cursor"]["last_id"]
    last_created_at = res.json()["next_cursor"]["last_created_at"]
    res = await async_client.get(
        "/v1/cars/",
        params={
            "limit": 1,
            "cursor_id": last_id,
            "created_at": last_created_at,
        },
    )
    assert res.status_code == 200
    assert isinstance(ParkingPriceTimeCursorSchema(**res.json()), ParkingPriceTimeCursorSchema)
    assert res.json()["parking_and_price_data"][0]["parking_data"]["number"] == "ak47TT"
    assert res.json()["has_more"] is False
    assert res.json()["next_cursor"] is None

    # ошибка при предаче cursor_id, без created_at
    res = await async_client.get("/v1/cars/", params={"limit": 1, "cursor_id": last_id})
    assert res.status_code == 422
    assert (
        "created_at должен быть передан, если передан cursor_id" in res.json()["detail"][0]["msg"]
    )
    assert res.json()["detail"][0]["type"] == "value_error"

    # ошибка при предаче created_at, без cursor_id
    res = await async_client.get("/v1/cars/", params={"limit": 1, "created_at": last_created_at})
    assert res.status_code == 422
    assert (
        "cursor_id должен быть передан, если передан created_at" in res.json()["detail"][0]["msg"]
    )
    assert res.json()["detail"][0]["type"] == "value_error"


async def test_get_car_parking_list_by_number(async_client):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    park = await async_client.post("/v1/cars/park/", json=park_car.model_dump())
    assert park.status_code == 201

    park_car_2 = CarParkSchema(mark="Toyota", model="Camry", number="us12kff", color="red")
    park_2 = await async_client.post("/v1/cars/park/", json=park_car_2.model_dump())
    assert park_2.status_code == 201

    res = await async_client.get(f"/v1/cars/{park_car_2.number}", params={"limit": 1})
    assert res.status_code == 200

    assert isinstance(ParkingPriceTimeCursorSchema(**res.json()), ParkingPriceTimeCursorSchema)
    assert res.json()["parking_and_price_data"][0]["parking_data"]["number"] == "us12kff"
    assert res.json()["has_more"] is False
    assert res.json()["next_cursor"] is None


async def test_get_car_parking_list_by_number_not_found(async_client):
    res = await async_client.get("/v1/cars/ak47TT")
    assert res.status_code == 200
    assert res.json()["parking_and_price_data"] == []
    assert res.json()["has_more"] is False
    assert res.json()["next_cursor"] is None


async def test_park_car(async_client):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    park = await async_client.post("/v1/cars/park/", json=park_car.model_dump())
    assert park.status_code == 201
    assert isinstance(ParkingReadSchema(**park.json()), ParkingReadSchema)

    parked_car = await async_client.get("/v1/cars/", params={"limit": 10})
    assert parked_car.status_code == 200
    assert parked_car.json()["parking_and_price_data"][0]["parking_data"]["number"] == "ak47TT"


async def test_park_parked_car(async_client):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    park = await async_client.post("/v1/cars/park/", json=park_car.model_dump())
    assert park.status_code == 201
    assert isinstance(ParkingReadSchema(**park.json()), ParkingReadSchema)

    park = await async_client.post("/v1/cars/park/", json=park_car.model_dump())
    assert park.status_code == 409
    assert park.json() == {"error": "car_already_parked", "message": "Машина уже припаркована."}


async def test_unpark_car(async_client):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    park = await async_client.post("/v1/cars/park/", json=park_car.model_dump())
    assert park.status_code == 201
    assert isinstance(ParkingReadSchema(**park.json()), ParkingReadSchema)

    unpark = await async_client.patch("/v1/cars/unpark/", json={"number": "ak47TT"})
    assert unpark.status_code == 200
    assert isinstance(CarParkingAndPriceSchema(**unpark.json()), CarParkingAndPriceSchema)


async def test_unpark_unparked_car_patched(async_client):
    with patch("app.domains.v1.cars.service.CarService.unpark_car") as mock_obj:
        mock_obj.side_effect = CarIsNotParkedException

        unpark_2 = await async_client.patch("/v1/cars/unpark/", json={"number": "ak47TT"})
        assert unpark_2.status_code == 400
        mock_obj.assert_called_once()


async def test_unpark_unparked_car(async_client):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    park = await async_client.post("/v1/cars/park/", json=park_car.model_dump())
    assert park.status_code == 201
    assert isinstance(ParkingReadSchema(**park.json()), ParkingReadSchema)

    unpark = await async_client.patch("/v1/cars/unpark/", json={"number": "ak47TT"})
    assert unpark.status_code == 200
    assert isinstance(CarParkingAndPriceSchema(**unpark.json()), CarParkingAndPriceSchema)

    unpark_again = await async_client.patch("/v1/cars/unpark/", json={"number": "ak47TT"})

    assert unpark_again.status_code == 400
    assert unpark_again.json() == {
        "error": "car_is_not_parked",
        "message": "Машина еще не припаркована.",
    }


async def test_unpark_car_not_found_patched(async_client):
    with patch("app.domains.v1.cars.service.CarService.unpark_car") as mock_obj:
        mock_obj.side_effect = CarNotFoundException

        unpark_2 = await async_client.patch("/v1/cars/unpark/", json={"number": "ak47TT"})
        assert unpark_2.status_code == 404
        mock_obj.assert_called_once()


async def test_unpark_car_not_found(async_client):
    unpark = await async_client.patch("/v1/cars/unpark/", json={"number": "ak47TT"})
    assert unpark.status_code == 404
    assert unpark.json() == {
        "error": "car_not_found",
        "message": "Машина не найдена.",
    }
