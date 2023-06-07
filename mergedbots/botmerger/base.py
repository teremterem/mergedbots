# pylint: disable=no-name-in-module
"""Base classes for the BotMerger library."""
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, UUID4, Field

if TYPE_CHECKING:
    from mergedbots.botmerger.models import MergedBot, MergedChannel


class BotMerger(ABC):
    """
    An abstract factory of everything else in this library and also the low level implementation of everything else
    in this library. Almost all the methods of almost all the other classes in this library are just a facade for
    methods of this class.
    """

    @abstractmethod
    def create_bot(self, alias: str, name: str = None, **kwargs) -> "MergedBot":
        """
        Create a bot. This version of bot creation function is meant to be called outside an async context (for ex.
        as a decorator to `respond` functions as they are being defined).
        """

    @abstractmethod
    async def create_bot_async(self, alias: str, name: str = None, **kwargs) -> "MergedBot":
        """Create a bot while inside an async context."""

    @abstractmethod
    async def find_bot(self, alias: str) -> "MergedBot":
        """Fetch a bot by its alias."""

    @abstractmethod
    async def find_or_create_user_channel(
        self,
        channel_type: str,
        channel_specific_id: Any,
        user_display_name: str,
        **kwargs,
    ) -> "MergedChannel":
        """
        Find or create a channel with a user as its owner. Parameters `channel_type` and `channel_specific_id` are
        used to look up the channel. Parameter `user_display_name` is used to create a user if the channel does not
        exist and is ignored if the channel already exists.
        """


class MergedObject(BaseModel):
    """
    Base class for all BotMerger models.

    ATTENTION! Models inheriting from this class should not be instantiated directly. Use the factory methods of
    `BotManager` instead.
    """

    class Config(BaseModel.Config):
        """
        Pydantic config.

        ATTENTION! If you define a new config for a model inheriting from this class, make sure to inherit from this
        config as well.
        """

        allow_mutation = False
        copy_on_model_validation = "none"
        arbitrary_types_allowed = True

    merger: BotMerger
    uuid: UUID4 = Field(default_factory=uuid4)
    # TODO freeze the contents of `extra_data` upon model creation recursively
    # TODO validate that all values in `extra_data` are json-serializable
    extra_fields: dict[str, Any] = Field(default_factory=dict)

    def __eq__(self, other: object) -> bool:
        """Check if two models represent the same concept."""
        if not isinstance(other, MergedObject):
            return False
        return self.uuid == other.uuid

    def __hash__(self) -> int:
        """The hash of the model is the hash of its uuid."""
        return hash(self.uuid)