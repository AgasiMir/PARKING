class PostException(Exception):
    detail = "Unknown Exception."

    def __init__(self, *args, **kwargs):
        super().__init__(self.detail, *args, **kwargs)


class CarNotFoundException(PostException):
    detail = "Машина не нейдена."


class CarIsAlreadyParkedException(PostException):
    detail = "Машина уже припаркована."


class CarIsNotParkedException(PostException):
    detail = "Машина еще не припаркована."
