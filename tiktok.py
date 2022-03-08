from typing import Any, Dict, List, Optional
import aiohttp
from attr import define
import attr
import dis_snek as dis
from dis_snek.client.utils.converters import timestamp_converter


@attr.s()
class TikTokObject(dis.DictSerializationMixin):
    @classmethod
    def _process_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        return super()._process_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        data = cls._process_dict(
            data,
        )
        return cls(**cls._filter_kwargs(data, cls._get_init_keys()))

    @classmethod
    def from_list(cls, datas: List[Dict[str, Any]]):
        return [
            cls.from_dict(
                data,
            )
            for data in datas
        ]

    def update_from_dict(self, data) -> None:
        data = self._process_dict(data)
        for key, value in self._filter_kwargs(data, self._get_keys()).items():
            # todo improve
            setattr(self, key, value)


@define
class Video(TikTokObject):
    download_url: str = attr.ib()
    cover_url: str = attr.ib()
    video_uri: str = attr.ib()

    @classmethod
    def _process_dict(cls, data: dict) -> dict:
        if play_addr := data.get("play_addr"):
            data["download_url"] = play_addr.get("url_list")[2]
            data["video_uri"] = play_addr.get("uri")
        if cover_addr := data.get("cover"):
            data["cover_url"] = cover_addr.get("url_list")[0]

        return data


@define
class Statistics(TikTokObject):
    play_count: int = attr.ib()
    like_count: int = attr.ib()
    comment_count: int = attr.ib()
    share_count: int = attr.ib()
    download_count: int = attr.ib()

    @classmethod
    def _process_dict(cls, data: dict) -> dict:
        if like_count := data.get("digg_count"):
            data["like_count"] = like_count
        if comment_count := data.get("comment_count"):
            data["comment_count"] = comment_count
        if share_count := data.get("share_count"):
            data["share_count"] = share_count
        if download_count := data.get("download_count"):
            data["download_count"] = download_count
        if play_count := data.get("play_count"):
            data["play_count"] = play_count
        return data


@define
class Music(TikTokObject):
    id: int = attr.ib(converter=int)
    title: str = attr.ib()
    play_url: str = attr.ib()
    website_url: str = attr.ib()
    cover_url: str = attr.ib()
    author: str = attr.ib()
    owner_nickname: str = attr.ib()
    owner_handle: str = attr.ib()
    owner_url: str = attr.ib()
    avatar_url: str = attr.ib(default=None)

    @classmethod
    def _process_dict(cls, data: dict) -> dict:
        if play_url := data.get("play_url"):
            data["play_url"] = play_url.get("url_list")[0]
        data["website_url"] = f"https://www.tiktok.com/music/id-{data.get('id')}"

        if cover_medium := data.get("cover_medium"):
            data["cover_url"] = cover_medium.get("url_list")[0]
        if avatar_thumb := data.get("avatar_thumb"):
            data["avatar_url"] = avatar_thumb.get("url_list")[0]
        if title := data.get("title"):
            data["title"] = title
        if id := data.get("id"):
            data["id"] = id
        data["owner_url"] = f"https://www.tiktok.com/@{data.get('owner_handle')}"

        return data


@define
class Author(TikTokObject):
    nickname: str = attr.ib()
    unique_id: str = attr.ib()
    url: str = attr.ib()
    avatar: str = attr.ib()

    @classmethod
    def _process_dict(cls, data: dict) -> dict:
        if unique_id := data.get("unique_id"):
            data["url"] = "https://www.tiktok.com/@" + unique_id

        if avatar_thumb := data.get("avatar_thumb"):
            data["avatar"] = avatar_thumb.get("url_list")[0]

        if nickname := data.get("nickname"):
            data["nickname"] = nickname
        if unique_id := data.get("unique_id"):
            data["unique_id"] = unique_id

        return data


@define
class Description(TikTokObject):
    raw: Optional[str] = attr.ib(default=None)
    cleaned: Optional[str] = attr.ib(default=None)
    """ No #hashtags """
    tags: Optional[List[str]] = attr.ib(default=None)

    @classmethod
    def _process_dict(cls, data: dict) -> dict:
        if raw := data.get("desc"):
            data["raw"] = raw
        data["cleaned"] = clean_desc(data.get("text_extra"), raw)
        data["tags"] = [
            f"{tag['hashtag_name']}"
            for tag in data.get("text_extra")
            if tag.get("type") == 1
        ]
        return data


def clean_desc(text_extra, desc) -> str:
    for tag in text_extra:
        desc: str
        desc = desc.replace(f"#{tag.get('hashtag_name')}", "", 1)
    return desc.strip()


@define
class TikTokData(TikTokObject):
    id: str = attr.ib()
    video: "Video" = attr.ib()
    created: "dis.Timestamp" = attr.ib(converter=timestamp_converter)
    statistics: "Statistics" = attr.ib()
    share_url: str = attr.ib()
    description: "Description" = attr.ib()
    music: "Music" = attr.ib()
    author: "Author" = attr.ib()

    @classmethod
    def _process_dict(cls, data: dict) -> "TikTokData":
        """data is the aweme_details dict"""

        if id := data.get("aweme_id"):
            data["id"] = int(id)
        if video := data.get("video"):
            data["video"] = Video.from_dict(video)
        if created := data.get("create_time"):
            data["created"] = created
        if statistics := data.get("statistics"):
            data["statistics"] = Statistics.from_dict(statistics)
        if share_url := data.get("share_url"):
            data["share_url"] = share_url.split(".html")[
                0
            ]  # remove unnesesary query params
        data["description"] = Description.from_dict(data)
        if music := data.get("music"):
            data["music"] = Music.from_dict(music)

        if author := data.get("author"):
            data["author"] = Author.from_dict(author)

        return data


async def get_tiktok(video_id: int) -> Optional["TikTokData"]:
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(5)) as session:
        async with session.get(
            f"https://api2.musical.ly/aweme/v1/aweme/detail/?aweme_id={video_id}",
            allow_redirects=False,
        ) as response:
            data = await response.json()
            if data.get("aweme_detail") and data.get("status_code") == 0:
                return TikTokData.from_dict(data["aweme_detail"])
            raise ValueError("Unable to get TikTok data")
