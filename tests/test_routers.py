from unittest.mock import patch

from app.domains.v1.cars.schemas import CarParkingAndPriceSchema, CarParkSchema, ParkingReadSchema
from app.errors.python_exceptions import CarIsNotParkedException, CarNotFoundException


async def test_get_cars_empty_list(async_client):
    res = await async_client.get("/v1/cars/")
    assert res.status_code == 200
    assert res.json() == []


async def test_get_cars(async_client):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    park = await async_client.post("/v1/cars/park/", json=park_car.model_dump())
    assert park.status_code == 201

    res = await async_client.get("/v1/cars/")
    assert res.status_code == 200
    assert isinstance(CarParkingAndPriceSchema(**res.json()[0]), CarParkingAndPriceSchema)


async def test_get_car_list_by_number(async_client):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    park = await async_client.post("/v1/cars/park/", json=park_car.model_dump())
    assert park.status_code == 201

    res = await async_client.get("/v1/cars/", params={"number": "ak47TT"})
    assert res.status_code == 200
    assert isinstance(CarParkingAndPriceSchema(**res.json()[0]), CarParkingAndPriceSchema)


async def test_get_car_list_by_number_not_found(async_client):
    res = await async_client.get("/v1/cars/", params={"number": "ak47TT"})
    assert res.status_code == 200
    assert res.json() == []


async def test_park_car(async_client):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    park = await async_client.post("/v1/cars/park/", json=park_car.model_dump())
    assert park.status_code == 201
    assert isinstance(ParkingReadSchema(**park.json()), ParkingReadSchema)


async def test_park_car_parked_car(async_client):
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


async def test_unpark_unparked_car(async_client):
    with patch("app.domains.v1.cars.service.CarService.unpark_car") as mock_obj:
        mock_obj.side_effect = CarIsNotParkedException

        unpark_2 = await async_client.patch("/v1/cars/unpark/", json={"number": "ak47TT"})
        assert unpark_2.status_code == 400
        mock_obj.assert_called_once()


async def test_unpark__car_not_found(async_client):
    with patch("app.domains.v1.cars.service.CarService.unpark_car") as mock_obj:
        mock_obj.side_effect = CarNotFoundException

        unpark_2 = await async_client.patch("/v1/cars/unpark/", json={"number": "ak47TT"})
        assert unpark_2.status_code == 404
        mock_obj.assert_called_once()
