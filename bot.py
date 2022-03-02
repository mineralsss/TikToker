from datetime import datetime
from enum import Enum
from math import trunc
from typing import List, Optional
from attr import define
import attr
import dis_snek as dis
import aiohttp
import re
from urllib.parse import urlsplit, parse_qs
import sqlite3
import datetime

bot = dis.Snake(
    intents=dis.Intents.MESSAGES | dis.Intents.DEFAULT,
    sync_interactions=True,
    debug_scope=1234,
    delete_unused_application_cmds=False,
)


conn = sqlite3.connect("cache.db")
c = conn.cursor()
c.execute(
    "CREATE TABLE IF NOT EXISTS cache (video_id INTEGER PRIMARY KEY, timestamp TEXT, tiktoker_slug TEXT)"
)


@dis.listen(dis.events.MessageCreate)
async def on_message_create(event: dis.events.MessageCreate):
    if event.message.author.id == bot.user.id:
        return
    content = event.message.content
    link = check_for_link(content)
    if not link:
        return
    if link.type == VideoIdType.SHORT:
        video_id = await get_video_id(link.url)
    else:
        video_id = link.id
    aweme = await get_aweme_data(video_id)
    direct_download = aweme["aweme_detail"]["video"]["play_addr"]["url_list"][
        2
    ]  # NOTE: Index 2 is the default CDN
    short_url = await get_short_url(direct_download, video_id)
    more_info_btn = dis.Button(
        dis.ButtonStyles.GRAY,
        "Info",
        "🌐",
        custom_id=f"id{video_id}",
    )
    delete_msg_btn = dis.Button(
        dis.ButtonStyles.RED,
        emoji="🗑️",
        custom_id="delete_msg",
    )
    await event.message.reply(short_url, components=[more_info_btn, delete_msg_btn])


@dis.listen(dis.events.Button)
async def on_button_click(event: dis.events.Button):
    ctx = event.context
    if ctx.custom_id == "delete_msg":
        await ctx.message.delete()
    elif ctx.custom_id.startswith("id"):
        await ctx.defer(ephemeral=True)

        data = await get_aweme_data(int(ctx.custom_id[2:]))

        avatar = data["aweme_detail"]["author"]["avatar_thumb"]["url_list"][0]
        nickname = data["aweme_detail"]["author"]["nickname"]
        author_url = (
            "https://www.tiktok.com/@" + data["aweme_detail"]["author"]["unique_id"]
        )
        play_count = data["aweme_detail"]["statistics"]["play_count"]
        like_count = data["aweme_detail"]["statistics"]["digg_count"]
        comment_count = data["aweme_detail"]["statistics"]["comment_count"]
        share_count = data["aweme_detail"]["statistics"]["share_count"]
        download_count = data["aweme_detail"]["statistics"]["download_count"]
        link_to_video = "https://m.tiktok.com/v/" + data["aweme_detail"]["aweme_id"]
        origin_cover = data["aweme_detail"]["video"]["origin_cover"]["url_list"][0]

        embed = dis.Embed("TikTok Details")

        embed.set_author(name=nickname, icon_url=avatar, url=author_url)
        embed.description = link_to_video
        embed.set_thumbnail(url=origin_cover)
        embed.add_field("Views 👁️", play_count, True)
        embed.add_field("Likes ❤️", like_count, True)
        embed.add_field("Comments 💬", comment_count, True)
        embed.add_field("Shares 🔃", share_count, True)
        embed.add_field("Downloads 📥", download_count, True)
        embed.add_field(
            "Created",
            dis.Timestamp.fromtimestamp(data["aweme_detail"]["create_time"]),
            True,
        )
        direct_download = data["aweme_detail"]["video"]["play_addr"]["url_list"][
            2
        ]  # NOTE: Index 2 is the default CDN

        c.execute(
            "SELECT * FROM cache WHERE video_id = ?",
            (data["aweme_detail"]["aweme_id"],),
        )
        if entry := c.fetchone():
            if int(entry[1]) < trunc(
                datetime.datetime.timestamp(datetime.datetime.now())
            ) or not ctx.message.content.endswith(entry[2]):
                await ctx.send(embed=embed)
                short_url = await get_short_url(
                    direct_download, data["aweme_detail"]["aweme_id"]
                )
                edit_me = ctx.channel.get_message(ctx.message.id)
                await edit_me.edit(content=short_url)
                return
            else:
                await ctx.send(embed=embed)
        else:
            await ctx.send(embed=embed)
            short_url = await get_short_url(
                direct_download, data["aweme_detail"]["aweme_id"]
            )
            edit_me = ctx.channel.get_message(ctx.message.id)
            await edit_me.edit(content=short_url)
            return


# @dis.slash_command("tiktok")
# @dis.slash_option("url", "url of the video", dis.OptionTypes.STRING, required=True)
# async def tiktok(ctx: dis.InteractionContext, url: str):
#     """
#     Gets the direct download link of a TikTok video.
#     """
#     link = check_for_link(url)
#     if not link: return
#     if link.type == VideoIdType.SHORT:
#         video_id = await get_video_id(link.url)
#     else:
#         video_id = link.id
#     aweme = await get_aweme_data(video_id)
#     direct_download = aweme["aweme_detail"]["video"]["play_addr"]["url_list"][2] # NOTE: Index 2 is the default CDN
#     short_url = await shorten_url(direct_download)
#     return await ctx.send(short_url)


async def get_short_url(url: str, video_id: int) -> str:
    """
    Shortens a url if not in cache.

    args:
        url: The url to shorten.

    returns:
        The shortened url.
    """
    c.execute("SELECT * FROM cache WHERE video_id=?", (video_id,))
    if data := c.fetchone():
        if int(data[1]) > trunc(datetime.datetime.timestamp(datetime.datetime.now())):
            return "https://tiktoker.win/" + data[2]

    async with aiohttp.ClientSession() as session:
        split_url = urlsplit(url)
        if split_url.path == "/aweme/v1/play/":  # NOTE: This is to save some bytes lol
            params_dict = parse_qs(split_url.query)
            url = f"{split_url.scheme}://{split_url.netloc}/aweme/v1/play/?video_id={params_dict['video_id'][0]}"
        async with session.post(
            "https://tiktoker.win/links", json={"url": url}, headers={"Authorization": "special_key"} # TODO: Make this an env variable
        ) as response:
            data = await response.json()
            c.execute(
                "REPLACE INTO cache VALUES (?, ?, ?)",
                (
                    video_id,
                    trunc(
                        datetime.datetime.timestamp(
                            datetime.datetime.now() + datetime.timedelta(days=3)
                        )
                    ),  # NOTE: Will expire in 3 days
                    data.get("slug"),
                ),
            )
            conn.commit()
            return data.get("shortened")


async def get_video_id(url: str) -> int:
    """
    Gets the video id from short url.

    args:
        url: The url to get the id from.

    returns:
        The video id.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url, allow_redirects=False) as response:
            if location := response.headers.get("Location"):
                if link := check_for_link(location):
                    return link.id


async def get_aweme_data(video_id: int = None) -> dict:
    """Downlods the video.

    args:
        video_id: The video id.

    returns:
        The video data.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api2.musical.ly/aweme/v1/aweme/detail/?aweme_id={video_id}",
            allow_redirects=False,
        ) as response:
            return await response.json()


long_link_regex = r"(?P<http>http:|https:\/\/)?(www\.)?tiktok\.com\/(@.{1,24})\/video\/(?P<id>\d{15,30})"
short_link_regex = (
    r"(?P<http>http:|https:\/\/)?(\w{2})\.tiktok.com\/(?P<short_id>\w{5,15})"
)
medium_link_regex = r"(?P<http>http:|https:\/\/)?m\.tiktok\.com\/v\/(?P<id>\d{15,30})"


def check_for_link(content: str) -> Optional["LinkData"]:
    """
    Checks if the content has a TikTok video.

    args:
        content: The content to check.

    returns:
        LinkData
    """
    long_match = re.search(long_link_regex, content)
    short_match = re.search(short_link_regex, content)
    medium_match = re.search(medium_link_regex, content)

    if long_match:
        if not long_match.group("http"):
            return LinkData.from_list(
                [
                    VideoIdType.LONG,
                    long_match.group("id"),
                    f"https://{long_match.group(0)}",
                ]
            )
        return LinkData.from_list(
            [VideoIdType.LONG, long_match.group("id"), long_match.group(0)]
        )
    if short_match:
        if not short_match.group("http"):
            return LinkData.from_list(
                [
                    VideoIdType.SHORT,
                    short_match.group("short_id"),
                    f"https://{short_match.group(0)}",
                ]
            )
        return LinkData.from_list(
            [VideoIdType.SHORT, short_match.group("short_id"), short_match.group(0)]
        )
    if medium_match:
        if not medium_match.group("http"):
            return LinkData.from_list(
                [
                    VideoIdType.MEDIUM,
                    medium_match.group("id"),
                    f"https://{medium_match.group(0)}",
                ]
            )
        return LinkData.from_list(
            [VideoIdType.MEDIUM, medium_match.group("id"), medium_match.group(0)]
        )
    return None


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


bot.start("token") # TODO: Make this an env variable
