"""Internal Event Layer (network_architecture.md §Event Layer).

A minimal synchronous pub/sub bus. Deliberately not a queue/asyncio.Queue-based system:
subscribers (Dashboard via Gateway, logging) need to react to events as they happen,
and the emitting code (ConnectionManager, HeartbeatManager, Scheduler) doesn't need to
know who's listening or block on delivery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class EventType(Enum):
    DEVICE_CONNECTED = "DEVICE_CONNECTED"
    DEVICE_DISCONNECTED = "DEVICE_DISCONNECTED"
    RECORDING_STARTED = "RECORDING_STARTED"
    RECORDING_STOPPED = "RECORDING_STOPPED"
    UPLOAD_STARTED = "UPLOAD_STARTED"
    UPLOAD_COMPLETED = "UPLOAD_COMPLETED"
    STORAGE_WARNING = "STORAGE_WARNING"
    BATTERY_WARNING = "BATTERY_WARNING"
    CONNECTION_LOST = "CONNECTION_LOST"


@dataclass(frozen=True)
class Event:
    type: EventType
    device_id: str
    detail: str = ""


Listener = Callable[[Event], None]


@dataclass
class EventBus:
    _listeners: list[Listener] = field(default_factory=list)

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        """Registers a listener; returns an unsubscribe callback."""
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def emit(self, event: Event) -> None:
        for listener in list(self._listeners):
            listener(event)
