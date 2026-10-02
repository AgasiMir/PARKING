from app.park_price.pricing_strategies import (
    LongTimeParkPrice,
    MidTimeParkPrice,
    ParkPrice,
    ShortTimeParkPrice,
)


def set_pricing_strategies(park_time: float):

    if park_time < 60:
        return "short"
    elif park_time < 120:
        return "mid"
    else:
        return "long"


pricing_strategies_map = {
    "short": ShortTimeParkPrice(),
    "mid": MidTimeParkPrice(),
    "long": LongTimeParkPrice(),
}


class Pricing:
    def __init__(self, park_price: ParkPrice):
        self.park_price = park_price

    def get_park_price(self, park_time: float) -> float:
        return self.park_price.get_park_price(park_time)
