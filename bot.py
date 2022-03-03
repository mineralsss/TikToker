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

from dotenv import get_key

from dis_snek.ext.paginators import Paginator

bot = dis.Snake(
    intents=dis.Intents.MESSAGES | dis.Intents.DEFAULT,
    sync_interactions=True,
    debug_scope=780435741650059264,
    delete_unused_application_cmds=True,
)


conn = sqlite3.connect("database.db")


def dict_factory(cursor, row):  # NOTE: dict instead of tuple
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


conn.row_factory = dict_factory
c = conn.cursor()
c.execute(
    "CREATE TABLE IF NOT EXISTS cache (video_id INTEGER PRIMARY KEY, timestamp TEXT, tiktoker_slug TEXT)"
)
c.execute(
    "CREATE TABLE IF NOT EXISTS config (guild_id INTEGER PRIMARY KEY, auto_embed BOOLEAN DEFAULT 1, delete_origin BOOLEAN DEFAULT 0, suppress_origin_embed BOOLEAN DEFAULT 1)"
)
c.execute(
    "CREATE TABLE IF NOT EXISTS usage_data (guild_id INTEGER, user_id INTEGER, video_id INTEGER)"
)
c.execute("CREATE TABLE IF NOT EXISTS opted_out (user_id INTEGER PRIMARY KEY)")


@define
class GuildConfig:
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

    @classmethod
    def from_dict(cls, data: dict) -> "GuildConfig":
        return cls(**data)


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


@dis.slash_command("help", "All the help you need")
async def help(ctx: dis.InteractionContext):
    embeds = [
        dis.Embed(
            title="Tiktoker",
            description="Tiktoker is a bot that allows you to send Tiktok videos to your discord server.",
            color="#00FFF0",
            fields=[
                dis.EmbedField("Help Menu", "Below is some buttons that will guide you through some features of the bot.").to_dict(),
            ]
        ),
        dis.Embed(
            "Configuration",
            "Here are some configuration options for the bot.\nThese can be changed by using the `/config <option> <vaulue>` command.\nExample: `/config delete_origin:True`\nTo view the current configuration, use `/config` without any arguments.",
            color="#00FFF0",
            fields=[
                dis.EmbedField("Auto Embed", "When enabled, the bot will automatically embed the Tiktok link that is sent.").to_dict(),
                dis.EmbedField("Delete Origin", "When enabled and _Auto Embed_ is enabled, the bot will delete the message that sent the Tiktok link.").to_dict(),
                dis.EmbedField("Suppress Origin Embed", "Toggles the suppress origin embed feature.").to_dict(),
            ]
        )
    ]

    paginator = Paginator.create_from_embeds(bot, *embeds, timeout=20)
    paginator.default_button_color = dis.ButtonStyles.GRAY
    paginator.first_button_emoji = "<:first_arrow:948778200224370768>"
    paginator.last_button_emoji = "<:last_arrow:948778201264582806>"
    paginator.next_button_emoji = "<:next:948778200295673886>"
    paginator.back_button_emoji = "<:back:948778200257941576>"

    await paginator.send(ctx)
    
@dis.slash_command(name="privacy", description="Inform yourself on some of the data we collect.", sub_cmd_name="policy", sub_cmd_description="Review our Privacy Policy.")
async def privacy_policy(ctx: dis.InteractionContext):
    await ctx.send("This is a placeholder") #TODO: Make a privacy policy

@dis.slash_command(name="privacy", description="Inform yourself on some of the data we collect.", sub_cmd_name="options", sub_cmd_description="Choose what we can collect about you.")
async def privacy_options(ctx: dis.InteractionContext):
    await ctx.send("This is a placeholder") #TODO: Make a privacy policy


@dis.slash_command(
    "config",
    "Configures the bot for your server. (Leave options blank to view current settings)",
)
@dis.slash_option(
    "auto_embed", "Toggles auto embedding of tiktok links.", dis.OptionTypes.BOOLEAN
)
@dis.slash_option(
    "delete_origin",
    "Toggles deleting of the origin message. (When auto_embed True)",
    dis.OptionTypes.BOOLEAN,
)
@dis.slash_option(
    "suppress_origin_embed",
    "Toggles suppression of the origin message embed.",
    dis.OptionTypes.BOOLEAN,
)
async def setup_config(
    ctx: dis.InteractionContext,
    auto_embed: bool = None,
    delete_origin: bool = None,
    suppress_origin_embed: bool = None,
):
    """
    Sets up the config for the guild.
    """
    guild_id = ctx.guild.id
    config = get_guild_config(guild_id)
    if auto_embed is None and delete_origin is None and suppress_origin_embed is None:
        embed = dis.Embed(
            "Current Config", "To change a setting, use `/config <setting> <value>`"
        )
        embed.add_field("Auto Embed", "☑️" if config.auto_embed else "❌", inline=True)
        embed.add_field(
            "Delete Origin", "☑️" if config.delete_origin else "❌", inline=True
        )
        embed.add_field(
            "Suppress Origin Embed",
            "☑️" if config.suppress_origin_embed else "❌",
            inline=True,
        )
        await ctx.send(embed=embed)
        return

    if auto_embed is not None:
        config.auto_embed = auto_embed
    if delete_origin is not None:
        config.delete_origin = delete_origin
    if suppress_origin_embed is not None:
        config.suppress_origin_embed = suppress_origin_embed

    edit_guild_config(config)

    embed = dis.Embed(
        "Current Config", "To change a setting, use `/config <setting> <value>`"
    )
    embed.add_field("Auto Embed", "☑️" if config.auto_embed else "❌", inline=True)
    embed.add_field("Delete Origin", "☑️" if config.delete_origin else "❌", inline=True)
    embed.add_field(
        "Suppress Origin Embed",
        "☑️" if config.suppress_origin_embed else "❌",
        inline=True,
    )
    await ctx.send(embed=embed)


@dis.context_menu("Convert 📸", dis.CommandTypes.MESSAGE)
async def convert_video(ctx: dis.InteractionContext):
    link = check_for_link(ctx.target.content)
    if not link:
        return
    config = get_guild_config(ctx.guild.id)

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
        custom_id=f"v_id{video_id}",
    )
    delete_msg_btn = dis.Button(
        dis.ButtonStyles.RED,
        emoji="🗑️",
        custom_id=f"delete{ctx.author.id}",
    )
    if config.suppress_origin_embed:
        await ctx.target.suppress_embeds()
    await ctx.send(
        short_url + f" | [Origin]({ctx.target.jump_url})",
        components=[more_info_btn, delete_msg_btn],
    )


@dis.listen(dis.events.MessageCreate)
async def on_message_create(event: dis.events.MessageCreate):
    if event.message.author.id == bot.user.id:
        return
    content = event.message.content
    link = check_for_link(content)
    if not link:
        return

    config = get_guild_config(event.message.guild.id)

    if not config.auto_embed:
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
        custom_id=f"v_id{video_id}",
    )
    delete_msg_btn = dis.Button(
        dis.ButtonStyles.RED,
        emoji="🗑️",
        custom_id=f"delete{event.message.author.id}",
    )
    if config.delete_origin:
        await event.message.channel.send(
            short_url + f" | From: {event.message.author.mention}",
            components=[more_info_btn, delete_msg_btn],
            allowed_mentions=dis.AllowedMentions.none(),
        )
        await event.message.delete()
        return
    elif config.suppress_origin_embed:
        await event.message.suppress_embeds()
    await event.message.reply(short_url, components=[more_info_btn, delete_msg_btn])


@dis.listen(dis.events.Button)
async def on_button_click(event: dis.events.Button):
    ctx = event.context
    if ctx.custom_id.startswith("delete"):
        if dis.Permissions.MANAGE_MESSAGES in ctx.author.channel_permissions(
            ctx.channel
        ) or ctx.author.has_permission(dis.Permissions.MANAGE_MESSAGES):
            await ctx.message.delete()
        elif ctx.author.id == ctx.custom_id[6:]:
            await ctx.delete()
        else:
            await ctx.send(
                "You don't have the permissions to delete this message.", ephemeral=True
            )
    elif ctx.custom_id.startswith("v_id"):
        await ctx.defer(ephemeral=True)

        data = await get_aweme_data(int(ctx.custom_id[4:]))

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
        desc = data["aweme_detail"]["desc"]

        embed = dis.Embed(desc[:256] if desc != "" else None, description=link_to_video)

        embed.set_author(name=nickname, icon_url=avatar, url=author_url)
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

        download_btn = dis.Button(dis.ButtonStyles.URL, "Download", url=direct_download)

        audio_btn = dis.Button(
            dis.ButtonStyles.GRAY,
            "Audio",
            emoji="🎵",
            custom_id=f"m_id{data['aweme_detail']['aweme_id']}",
        )

        c.execute(
            "SELECT * FROM cache WHERE video_id = ?",
            (data["aweme_detail"]["aweme_id"],),
        )
        if entry := c.fetchone():
            if int(entry["timestamp"]) < trunc(
                datetime.datetime.timestamp(datetime.datetime.now())
            ) or not ctx.message.content.endswith(entry["tiktoker_slug"]):
                await ctx.send(embed=embed)
                short_url = await get_short_url(
                    direct_download, data["aweme_detail"]["aweme_id"]
                )
                edit_me = ctx.channel.get_message(ctx.message.id)
                await edit_me.edit(content=short_url)
                return
            else:
                await ctx.send(embed=embed, components=[download_btn, audio_btn])
        else:
            await ctx.send(embed=embed, components=[download_btn, audio_btn])
            short_url = await get_short_url(
                direct_download, data["aweme_detail"]["aweme_id"]
            )
            edit_me = ctx.channel.get_message(ctx.message.id)
            await edit_me.edit(content=short_url)
            return

    elif ctx.custom_id.startswith("m_id"):  # TODO: Use aweme instead of music
        await ctx.defer(ephemeral=True)
        data = await get_aweme_data(int(ctx.custom_id[4:]))
        if not data or not data.get("aweme_detail"):
            await ctx.send("Seems this audio has been deleted/taken down.")
            return
        music_data = data["aweme_detail"]["music"]
        play_link = music_data["play_url"]["url_list"][0]
        author_name = music_data["author"]
        if music_data["owner_handle"] != "":
            author_url = f"https://www.tiktok.com/@{music_data['owner_handle']}"
        else:
            author_url = None

        if music_data.get("avatar_medium"):
            author_avatar = music_data["avatar_medium"]["url_list"][0]
        else:
            author_avatar = None
        title = music_data["title"]

        cover = music_data["cover_medium"]["url_list"][0]

        embed = dis.Embed(
            title=title,
            url=f"https://www.tiktok.com/music/song-{music_data['id']}",
        )

        if extra_music_data := await get_music_data(music_data["id"]):
            video_count = extra_music_data["musicInfo"]["stats"]["videoCount"]
            embed.add_field(name="Video Count 📱", value=video_count, inline=False)

        embed.set_author(name=author_name, url=author_url, icon_url=author_avatar)
        embed.set_thumbnail(url=cover)

        await ctx.send(
            embed=embed,
            components=dis.Button(
                dis.ButtonStyles.URL, url=play_link, label="Download"
            ),
        )


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
        if int(data["timestamp"]) > trunc(
            datetime.datetime.timestamp(datetime.datetime.now())
        ):
            return "https://tiktoker.win/" + data["tiktoker_slug"]

    async with aiohttp.ClientSession() as session:
        split_url = urlsplit(url)
        if split_url.path == "/aweme/v1/play/":  # NOTE: This is to save some bytes lol
            params_dict = parse_qs(split_url.query)
            url = f"{split_url.scheme}://{split_url.netloc}/aweme/v1/play/?video_id={params_dict['video_id'][0]}"
        async with session.post(
            "https://tiktoker.win/links",
            json={"url": url},
            headers={
                "Authorization": get_key(".env", "TIKTOKER_API_KEY")
            },  # TODO: Make this an env variable
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
    """Gets the video data

    args:
        video_id: The video id.

    returns:
        The video data.
    """
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(2)) as session:
        async with session.get(
            f"https://api2.musical.ly/aweme/v1/aweme/detail/?aweme_id={video_id}",
            allow_redirects=False,
        ) as response:
            return await response.json()


async def get_music_data(music_id: int = None) -> Optional[dict]:
    """
    Gets the music data.

    args:
        music_id: The music id.

    returns:
        The music data.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://tiktok.com/api/music/detail/?language=en&musicId={music_id}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0"
            },
        ) as response:
            if response.status == 200:
                if data := await response.json():
                    if data.get("statusCode") == 10218:
                        return None
                    return data
                return data
            else:
                return None


def check_for_link(content: str) -> Optional["LinkData"]:
    """
    Checks if the content has a TikTok video.

    args:
        content: The content to check.

    returns:
        LinkData
    """
    try:
        long_match = re.search(
            r"(?P<http>http:|https:\/\/)?(www\.)?tiktok\.com\/(@.{1,24})\/video\/(?P<id>\d{15,30})",
            content,
        )
        short_match = re.search(
            r"(?P<http>http:|https:\/\/)?(\w{2})\.tiktok.com\/(?P<short_id>\w{5,15})",
            content,
        )
        medium_match = re.search(
            r"(?P<http>http:|https:\/\/)?m\.tiktok\.com\/v\/(?P<id>\d{15,30})", content
        )
    except TypeError as e:
        print(f"{content} is not a string")
        print(type(content))
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


def get_guild_config(guild_id: int) -> "GuildConfig":
    """
    Gets the guild config.

    args:
        guild_id: The guild id.

    returns:
        The guild config.
    """
    c.execute("SELECT * FROM config WHERE guild_id=?", (guild_id,))
    if entry := c.fetchone():
        return GuildConfig.from_dict(entry)
    else:
        return insert_guild_config(GuildConfig(guild_id))


def insert_guild_config(config: "GuildConfig" = GuildConfig) -> "GuildConfig":
    c.execute(
        "INSERT INTO config VALUES (?, ?, ?, ?)",
        (
            config.guild_id,
            config.auto_embed,
            config.delete_origin,
            config.suppress_origin_embed,
        ),
    )
    conn.commit()
    return config


def edit_guild_config(config: "GuildConfig") -> "GuildConfig":
    get_guild_config(config.guild_id)
    c.execute(
        "UPDATE config SET auto_embed=?, delete_origin=?, suppress_origin_embed=? WHERE guild_id=?",
        (
            config.auto_embed,
            config.delete_origin,
            config.suppress_origin_embed,
            config.guild_id,
        ),
    )
    conn.commit()
    return config

def insert_usage_data(guild_id: int, user_id: int, video_id: int, message_id: int) -> None:
    """
    Inserts usage data.

    args:
        guild_id: The guild id.
        user_id: The user id.
        video_id: The video id.
        message_id: The message id with the video.
    """


    c.execute(
        "INSERT INTO usage_data VALUES (?, ?, ?, ?)",
        (guild_id, user_id, video_id, message_id),
    )
    conn.commit()


def get_opted_out(user_id: int) -> bool:
    c.execute("SELECT user_id FROM opted_out WHERE user_id=?", (user_id,))
    if opted_out := c.fetchone():
        return True
    else:
        return False


bot.start(get_key(".env", "TOKEN"))
