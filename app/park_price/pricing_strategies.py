from abc import ABC, abstractmethod


class ParkPrice(ABC):
    @abstractmethod
    def get_park_price(self, park_time: float) -> float:
        pass


class ShortTimeParkPrice(ParkPrice):
    def get_park_price(self, park_time: float) -> float:
        return 100 + park_time * 10


class MidTimeParkPrice(ParkPrice):
    def get_park_price(self, park_time: float) -> float:
        return 120 + park_time * 8


class LongTimeParkPrice(ParkPrice):
    def get_park_price(self, park_time: float) -> float:
        return 200 + park_time * 7
