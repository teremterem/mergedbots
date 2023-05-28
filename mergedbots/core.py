# pylint: disable=no-name-in-module
"""BotManager implementations."""
from abc import abstractmethod
from typing import Any

from pydantic import PrivateAttr, UUID4

from mergedbots.errors import BotHandleTakenError, BotNotFoundError
from mergedbots.models import BotManager, MergedParticipant, MergedUser, MergedBot, MergedMessage, MergedObject

ObjectKey = Any | tuple[Any, ...]


class BotManagerBase(BotManager):
    """
    An abstract factory of everything else in this library. This class implements the common functionality of all
    concrete BotManager implementations.
    """

    # TODO think about thread-safety ?

    def create_bot(self, handle: str, name: str = None, **kwargs) -> MergedBot:
        """Create a merged bot."""
        if self._get_bot(handle):
            raise BotHandleTakenError(f"bot with handle {handle!r} is already registered")

        if not name:
            name = handle
        bot = MergedBot(manager=self, handle=handle, name=name, **kwargs)

        self._register_bot(bot)
        return bot

    def find_bot(self, handle: str) -> MergedBot:
        """Fetch a bot by its handle."""
        bot = self._get_bot(handle)
        if not bot:
            raise BotNotFoundError(f"bot with handle {handle!r} does not exist")
        return bot

    def find_or_create_user(
        self,
        channel_type: str,
        channel_specific_id: Any,
        user_display_name: str,
        **kwargs,
    ) -> MergedUser:
        """Find or create a user."""
        key = self._generate_merged_user_key(channel_type=channel_type, channel_specific_id=channel_specific_id)
        user = self._get_object(key)
        self._assert_correct_obj_type_or_none(user, MergedUser, key)
        if user:
            return user

        user = MergedUser(manager=self, name=user_display_name, **kwargs)
        self._register_merged_object(user)
        self._register_object(key, user)
        return user

    def create_originator_message(  # pylint: disable=too-many-arguments
        self,
        channel_type: str,
        channel_id: Any,
        originator: MergedParticipant,
        content: str,
        is_visible_to_bots: bool = True,
        new_conversation: bool = False,
        **kwargs,
    ) -> MergedMessage:
        """
        Create a new message from the conversation originator. The originator is typically a user, but it can also be
        a bot (which, for example, is trying to talk to another bot).
        """
        conv_tail_key = self._generate_conversation_tail_key(
            channel_type=channel_type,
            channel_id=channel_id,
        )
        previous_msg = None if new_conversation else self._get_object(conv_tail_key)
        self._assert_correct_obj_type_or_none(previous_msg, MergedMessage, conv_tail_key)

        message = MergedMessage(
            manager=self,
            channel_type=channel_type,
            channel_id=channel_id,
            sender=originator,
            content=content,
            is_visible_to_bots=is_visible_to_bots,
            is_still_typing=False,  # TODO use a wrapper object for this
            originator=originator,
            previous_msg=previous_msg,
            in_fulfillment_of=None,
            **kwargs,
        )
        self._register_merged_object(message)
        self._register_object(conv_tail_key, message)  # save the tail of the conversation
        return message

    @abstractmethod
    def _register_object(self, key: ObjectKey, value: Any) -> None:
        """Register an object."""

    @abstractmethod
    def _get_object(self, key: ObjectKey) -> Any | None:
        """Get an object by its key."""

    def _register_merged_object(self, obj: MergedObject) -> None:
        """Register a merged object."""
        self._register_object(obj.uuid, obj)

    def _get_merged_object(self, uuid: UUID4) -> MergedObject | None:
        """Get a merged object by its uuid."""
        obj = self._get_object(uuid)
        self._assert_correct_obj_type_or_none(obj, MergedObject, uuid)
        return obj

    def _register_bot(self, bot: MergedBot) -> None:
        """Register a bot."""
        self._register_merged_object(bot)
        self._register_object(self._generate_merged_bot_key(bot.handle), bot)

    def _get_bot(self, handle: str) -> MergedBot | None:
        """Get a bot by its handle."""
        key = self._generate_merged_bot_key(handle)
        bot = self._get_object(key)
        self._assert_correct_obj_type_or_none(bot, MergedBot, key)
        return bot

    # noinspection PyMethodMayBeStatic
    def _generate_merged_bot_key(self, handle: str) -> tuple[str, str]:
        """Generate a key for a bot."""
        return "bot_by_handle", handle

    # noinspection PyMethodMayBeStatic
    def _generate_merged_user_key(self, channel_type: str, channel_specific_id: Any) -> tuple[str, str, str]:
        """Generate a key for a user."""
        return "user_by_channel", channel_type, channel_specific_id

    # noinspection PyMethodMayBeStatic
    def _generate_conversation_tail_key(self, channel_type: str, channel_id: Any) -> tuple[str, str, str]:
        """Generate a key for a conversation tail."""
        return "conv_tail_by_channel", channel_type, channel_id

    # noinspection PyMethodMayBeStatic
    def _assert_correct_obj_type_or_none(self, obj: Any, expected_type: type, key: Any) -> None:
        """Assert that the object is of the expected type or None."""
        if obj and not isinstance(obj, expected_type):
            raise TypeError(
                f"wrong type of object by the key {key!r}: "
                f"expected {expected_type.__name__!r}, got {type(obj).__name__!r}",
            )


class InMemoryBotManager(BotManagerBase):
    """An in-memory object manager."""

    _objects: dict[ObjectKey, Any] = PrivateAttr(default_factory=dict)

    def _register_object(self, key: ObjectKey, value: Any) -> None:
        """Register an object."""
        self._objects[key] = value

    def _get_object(self, key: ObjectKey) -> Any | None:
        """Get an object by its key."""
        return self._objects.get(key)


# TODO RedisBotManager ? SQLAlchemyBotManager ? A hybrid of the two ? Any other ideas ?
