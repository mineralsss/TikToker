from beanie import Document, Indexed
from datetime import datetime
import dis_snek as dis
from typing import Optional


class Config(Document, dis.DictSerializationMixin):
    guild_id: Indexed(int, unique=True)
    auto_embed: bool = True
    delete_origin: bool = False
    suppress_origin_embed: bool = True
    language: str = "en"


class UsageData(Document):
    guild_id: Indexed(int)
    user_id: Optional[int] = None
    video_id: Indexed(int)
    message_id: Optional[int] = None
    timestamp: Indexed(int) = datetime.now().timestamp()


class Shortener(Document, dis.DictSerializationMixin):
    video_uri: Indexed(str, unique=True)
    slug: Indexed(str, unique=True)
    shortened_url: Indexed(str)  # full url


class OptedOut(Document):
    user_id: Indexed(int, unique=True)
