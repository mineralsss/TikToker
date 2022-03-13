from enum import Enum
from typing import List
from attr import define
import attr
from dis_snek import DictSerializationMixin


@define
class LinkData:
    """
    A class to store the link data.
    """

    type: int = attr.ib()
    id: int = attr.ib()
    url: str = attr.ib()

    @classmethod
    def from_list(cls, link: List[int | str | str]) -> "LinkData":
        """
        Creates a LinkData from a list.

        args:
            link: The list to create the data from.

        returns:
            A LinkData object.
        """
        if len(link) != 3:
            raise ValueError("Invalid link")
        return cls(*link)


class VideoIdType(Enum):
    LONG = 0  # https://www.tiktok.com/@placeholder/video/7068971038273423621
    SHORT = 1  # https://vm.tiktok.com/PTPdh1wVay/
    MEDIUM = 2  # https://m.tiktok.com/v/7068971038273423621.html
    FYP = 3 # https://www.tiktok.com/foryou?_r=1&is_from_webapp=v1&item_id=7068971038273423621&source=h5_m#/@yakmofo123/video/7068971038273423621
