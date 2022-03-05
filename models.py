from enum import Enum
from typing import List
from attr import define
import attr
from dis_snek import DictSerializationMixin


@define
class GuildConfig(DictSerializationMixin):
    guild_id: int = attr.ib(default=None)
    auto_embed: bool = attr.ib(
        default=True, validator=attr.validators.instance_of(bool), converter=bool
    )
    """ Automaticly embeds the sent link """
    delete_origin: bool = attr.ib(
        default=False, validator=attr.validators.instance_of(bool), converter=bool
    )
    """ Deletes the message that sent the link """
    suppress_origin_embed: bool = attr.ib(
        default=True, validator=attr.validators.instance_of(bool), converter=bool
    )
    """ Suppresses the embed of the origin message """


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
