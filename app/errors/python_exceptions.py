class ParkingException(Exception):
    detail = "Unknown Exception."

    def __init__(self, *args, **kwargs):
        super().__init__(self.detail, *args, **kwargs)


class CarNotFoundException(ParkingException):
    detail = "Машина не найдена."


class CarIsAlreadyParkedException(ParkingException):
    detail = "Машина уже припаркована."


class CarIsNotParkedException(ParkingException):
    detail = "Машина еще не припаркована."
