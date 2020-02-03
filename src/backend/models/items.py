# SPDX-License-Identifier: LGPL-3.0-or-later

"""`ModelItem` subclasses definitions."""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, Union
from uuid import UUID

import lxml  # nosec
import nio

from ..html_markdown import HTML_PROCESSOR
from ..utils import AutoStrEnum, auto
from .model_item import ModelItem

ZeroDate              = datetime.fromtimestamp(0)
OptionalExceptionType = Union[Type[None], Type[Exception]]


class TypeSpecifier(AutoStrEnum):
    """Enum providing clarification of purpose for some matrix events."""

    Unset            = auto()
    ProfileChange    = auto()
    MembershipChange = auto()


@dataclass
class Account(ModelItem):
    """A logged in matrix account."""

    id:              str      = field()
    display_name:    str      = ""
    avatar_url:      str      = ""
    first_sync_done: bool     = False
    profile_updated: datetime = ZeroDate

    def __lt__(self, other: "Account") -> bool:
        """Sort by display name or user ID."""
        name       = self.display_name or self.id[1:]
        other_name = other.display_name or other.id[1:]
        return name.lower() < other_name.lower()


@dataclass
class Room(ModelItem):
    """A matrix room we are invited to, are or were member of."""

    id:             str  = field()
    given_name:     str  = ""
    display_name:   str  = ""
    main_alias:     str  = ""
    avatar_url:     str  = ""
    plain_topic:    str  = ""
    topic:          str  = ""
    inviter_id:     str  = ""
    inviter_name:   str  = ""
    inviter_avatar: str  = ""
    left:           bool = False

    typing_members: List[str] = field(default_factory=list)

    federated:       bool = True
    encrypted:       bool = False
    invite_required: bool = True
    guests_allowed:  bool = True

    can_invite:           bool = False
    can_send_messages:    bool = False
    can_set_name:         bool = False
    can_set_topic:        bool = False
    can_set_avatar:       bool = False
    can_set_encryption:   bool = False
    can_set_join_rules:   bool = False
    can_set_guest_access: bool = False

    last_event_date: datetime = ZeroDate

    def __lt__(self, other: "Room") -> bool:
        """Sort by join state, then descending last event date, then name.

        Invited rooms are first, then joined rooms, then left rooms.
        Within these categories, sort by last event date (room with recent
        messages are first), then by display names.
        """

        # Left rooms may still have an inviter_id, so check left first.
        return (
            self.left,
            other.inviter_id,
            other.last_event_date,
            (self.display_name or self.id).lower(),
        ) < (
            other.left,
            self.inviter_id,
            self.last_event_date,
            (other.display_name or other.id).lower(),
        )


@dataclass
class Member(ModelItem):
    """A member in a matrix room."""

    id:              str      = field()
    display_name:    str      = ""
    avatar_url:      str      = ""
    typing:          bool     = False
    power_level:     int      = 0
    invited:         bool     = False
    profile_updated: datetime = ZeroDate

    def __lt__(self, other: "Member") -> bool:
        """Sort by power level, then by display name/user ID."""

        name       = self.display_name or self.id[1:]
        other_name = other.display_name or other.id[1:]

        return (
            self.invited, other.power_level, name.lower(),
        ) < (
            other.invited, self.power_level, other_name.lower(),
        )


    @property
    def filter_string(self) -> str:
        """Filter members based on display name."""
        return self.display_name


class UploadStatus(AutoStrEnum):
    """Enum describing the status of an upload operation."""

    Uploading = auto()
    Caching   = auto()
    Error     = auto()


@dataclass
class Upload(ModelItem):
    """Represent a running or failed file upload operation."""

    id:       UUID                = field()
    task:     asyncio.Task        = field()
    monitor:  nio.TransferMonitor = field()
    filepath: Path                = field()

    total_size: int       = 0
    uploaded:   int       = 0
    speed:      float     = 0
    time_left:  timedelta = timedelta(0)

    status:     UploadStatus          = UploadStatus.Uploading
    error:      OptionalExceptionType = type(None)
    error_args: Tuple[Any, ...]       = ()

    start_date: datetime = field(init=False, default_factory=datetime.now)


    def __lt__(self, other: "Upload") -> bool:
        """Sort by the start date, from newest upload to oldest."""

        return self.start_date > other.start_date


@dataclass
class Event(ModelItem):
    """A matrix state event or message."""

    id:            str                 = field()
    event_id:      str                 = field()
    source:        Optional[nio.Event] = field()
    date:          datetime            = field()
    sender_id:     str                 = field()
    sender_name:   str                 = field()
    sender_avatar: str                 = field()

    content:        str = ""
    inline_content: str = ""
    reason:         str = ""

    type_specifier: TypeSpecifier = TypeSpecifier.Unset

    target_id:     str = ""
    target_name:   str = ""
    target_avatar: str = ""

    is_local_echo:    bool                      = False
    local_event_type: Optional[Type[nio.Event]] = None

    media_url:        str            = ""
    media_title:      str            = ""
    media_width:      int            = 0
    media_height:     int            = 0
    media_duration:   int            = 0
    media_size:       int            = 0
    media_mime:       str            = ""
    media_crypt_dict: Dict[str, Any] = field(default_factory=dict)

    thumbnail_url:        str            = ""
    thumbnail_width:      int            = 0
    thumbnail_height:     int            = 0
    thumbnail_crypt_dict: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.inline_content:
            self.inline_content = \
                HTML_PROCESSOR.filter(self.content, inline=True)


    def __lt__(self, other: "Event") -> bool:
        """Sort by date in descending order, from newest to oldest."""

        return self.date > other.date

    @property
    def event_type(self) -> Type:
        """Type of the source nio event used to create this `Event`."""

        if self.local_event_type:
            return self.local_event_type

        return type(self.source)

    @property
    def links(self) -> List[str]:
        """List of URLs (`<a href=...>` tags) present in the event content."""

        urls: List[str] = []

        if self.content.strip():
            urls += [link[2] for link in lxml.html.iterlinks(self.content)]

        if self.media_url:
            urls.append(self.media_url)

        return urls

    @property
    def serialized(self) -> Dict[str, Any]:
        dct = super().serialized
        del dct["source"]
        del dct["local_event_type"]
        return dct


@dataclass
class Device(ModelItem):
    """A matrix user's device. This class is currently unused."""

    id:             str  = field()
    ed25519_key:    str  = field()
    trusted:        bool = False
    blacklisted:    bool = False
    display_name:   str  = ""
    last_seen_ip:   str  = ""
    last_seen_date: str  = ""
