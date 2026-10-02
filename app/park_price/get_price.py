from datetime import datetime

from app.park_price.pricing_strategies import (
    LongTimeParkPrice,
    MidTimeParkPrice,
    ParkPrice,
    ShortTimeParkPrice,
)


def set_pricing_strategies(park_time: int):

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

    def get_park_price(self, park_time: int) -> float:
        return self.park_price.get_park_price(park_time)


if __name__ == "__main__":
    park = datetime(2026, 10, 2, 15, 00, 29)
    unpark = datetime(2026, 10, 2, 17, 0, 29)
    park_time = (unpark - park).seconds // 60

    set_pricing_strategy = pricing_strategies_map[set_pricing_strategies(park_time)]
    total_price = Pricing(set_pricing_strategy).get_park_price(park_time)
    print(total_price)
