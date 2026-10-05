from pytest import mark, param

from app.park_price.get_price import pricing_strategies_map, set_pricing_strategies
from app.park_price.pricing_strategies import (
    LongTimeParkPrice,
    MidTimeParkPrice,
    ShortTimeParkPrice,
)


@mark.parametrize(
    "park_time, expected",
    [
        param(1, "short", id="short-lower"),
        param(30, "short", id="short"),
        param(59, "short", id="short-upper"),
        param(60, "mid", id="mid-lower"),  # граница: ровно 60 мин -> mid
        param(61, "mid", id="mid"),
        param(119, "mid", id="mid-upper"),
        param(120, "long", id="long-lower"),  # граница: ровно 120 мин -> long
        param(121, "long", id="long"),
    ],
)
async def test_set_pricing_strategies(park_time, expected):
    assert set_pricing_strategies(park_time) == expected


@mark.parametrize(
    "park_time, expected_class",
    [
        param(1, ShortTimeParkPrice, id="short-lower"),
        param(30, ShortTimeParkPrice, id="short"),
        param(59, ShortTimeParkPrice, id="short-upper"),
        param(60, MidTimeParkPrice, id="mid-lower"),
        param(61, MidTimeParkPrice, id="mid"),
        param(119, MidTimeParkPrice, id="mid-upper"),
        param(120, LongTimeParkPrice, id="long-lower"),
        param(121, LongTimeParkPrice, id="long"),
    ],
)
async def test_pricing_strategies_map(park_time, expected_class):
    assert isinstance(pricing_strategies_map[set_pricing_strategies(park_time)], expected_class)
