from enum import Enum
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QDateTime, QSortFilterProxyModel

from ..pyqt_future import PyQtFuture
from .list_item import ListItem
from .list_model import ListModel


class Account(ListItem):
    _required_init_values = {"userId", "roomCategories"}
    _constant             = {"userId", "roomCategories"}

    userId:         str       = ""
    roomCategories: ListModel = ListModel()


class RoomCategory(ListItem):
    _required_init_values = {"name", "rooms", "sortedRooms"}
    _constant             = {"name", "rooms", "sortedRooms"}

    name:        str                   = ""
    rooms:       ListModel             = ListModel()
    sortedRooms: QSortFilterProxyModel = QSortFilterProxyModel()


class Room(ListItem):
    _required_init_values = {"roomId", "displayName", "members"}
    _constant             = {"roomId", "members"}

    roomId:            str                 = ""
    displayName:       str                 = ""
    topic:             Optional[str]       = None
    lastEventDateTime: Optional[QDateTime] = None
    typingMembers:     List[str]           = []
    members:           ListModel           = ListModel()

    inviter:   Optional[Dict[str, str]] = None
    leftEvent: Optional[Dict[str, str]] = None


# ----------

class RoomEvent(ListItem):
    _required_init_values = {"eventId", "type", "dict", "dateTime"}
    _constant             = {"type"}

    eventId:     str            = ""
    type:        str            = ""
    dict:        Dict[str, Any] = {}
    dateTime:    QDateTime      = QDateTime()
    isLocalEcho: bool           = False


# ----------

class User(ListItem):
    _required_init_values = {"userId", "devices"}
    _constant             = {"userId", "devices"}

    # Use PyQtFutures because the info might or might not need a request
    # to be fetched, and we don't want to block the UI in any case.
    # QML's property binding ability is used on the PyQtFuture.value
    userId:         str                  = ""
    displayName:    Optional[PyQtFuture] = None
    avatarUrl:      Optional[PyQtFuture] = None
    statusMessage:  Optional[PyQtFuture] = None
    devices:        ListModel            = ListModel()


class Trust(Enum):
    blacklisted = -1
    undecided   = 0
    trusted     = 1


class Device(ListItem):
    _required_init_values = {"deviceId", "ed25519Key"}
    _constant             = {"deviceId", "ed25519Key"}

    deviceId:     str                 = ""
    ed25519Key:   str                 = ""
    displayName:  Optional[str]       = None
    trust:        Trust               = Trust.undecided
    lastSeenIp:   Optional[str]       = None
    lastSeenDate: Optional[QDateTime] = None
