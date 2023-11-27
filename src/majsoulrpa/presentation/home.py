import datetime
import time
from logging import getLogger

from majsoulrpa._impl.browser import BrowserBase
from majsoulrpa._impl.db_client import DBClientBase
from majsoulrpa._impl.template import Template
from majsoulrpa.common import TimeoutType

from .presentation_base import (
    InconsistentMessage,
    PresentationBase,
    PresentationNotDetected,
    Timeout,
)
from .room import RoomHostPresentation

logger = getLogger(__name__)


class HomePresentation(PresentationBase):

    @staticmethod
    def _match_markers(screenshot: bytes, zoom_ratio: float) -> bool:
        for i in range(1, 4):
            template = Template.open_file(f"template/home/marker{i}",
                                          zoom_ratio)
            if not template.match(screenshot):
                return False
        return True

    @staticmethod
    def _close_notifications(
        browser: BrowserBase, timeout: TimeoutType,
    ) -> None:
        """Close home screen notifications if they are visible.
        """
        if isinstance(timeout, int | float):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.UTC) + timeout

        notification_close = Template.open_file(
            "template/home/notification_close", browser.zoom_ratio,
        )
        event_close = Template.open_file(
            "template/home/event_close", browser.zoom_ratio,
        )

        # TODO(Apricot S): Add processing for  # noqa: TD003
        # "Sign-in" and "Confirm" for limited time login bonus
        while True:
            if datetime.datetime.now(datetime.UTC) > deadline:
                msg = "Timeout."
                raise Timeout(msg, browser.get_screenshot())

            sct = browser.get_screenshot()

            x, y, score = notification_close.best_template_match(sct)
            if score >= notification_close.threshold:
                browser.click_region(
                    x, y,
                    notification_close.img_width,
                    notification_close.img_height,
                )
                time.sleep(1.0)
                continue

            x, y, score = event_close.best_template_match(sct)
            if score >= event_close.threshold:
                browser.click_region(
                    x, y,
                    event_close.img_width,
                    event_close.img_height,
                )
                time.sleep(1.0)
                continue

            break

    @staticmethod
    def _wait(browser: BrowserBase, timeout: TimeoutType) -> None:
        if isinstance(timeout, int | float):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.UTC) + timeout

        template = Template.open_file("template/home/marker0",
                                      browser.zoom_ratio)
        template.wait_until(browser, deadline)

        if not HomePresentation._match_markers(browser.get_screenshot(),
                                               browser.zoom_ratio):
            # Close any notifications displayed on the home screen.
            now = datetime.datetime.now(datetime.UTC)
            HomePresentation._close_notifications(browser, deadline - now)

            while True:
                if datetime.datetime.now(datetime.UTC) > deadline:
                    msg = "Timeout."
                    raise Timeout(msg, browser.get_screenshot())
                if HomePresentation._match_markers(browser.get_screenshot(),
                                                   browser.zoom_ratio):
                    break

    def __init__(  # noqa: PLR0912, PLR0915, C901
        self, browser: BrowserBase, db_client: DBClientBase,
        timeout: TimeoutType,
    ) -> None:
        super().__init__(browser, db_client)

        if isinstance(timeout, int | float):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.UTC) + timeout

        sct = browser.get_screenshot()
        if not HomePresentation._match_markers(sct, browser.zoom_ratio):
            msg = "Could not detect 'home'."
            raise PresentationNotDetected(msg, sct)

        num_login_beats = 0
        while True:
            now = datetime.datetime.now(datetime.UTC)
            message = self._db_client.dequeue_message(deadline - now)
            if message is None:
                msg = "Timeout."
                raise Timeout(msg, sct)
            _, name, _, _, _ = message

            match name:
                case (".lq.Lobby.heatbeat"
                      | ".lq.NotifyAccountUpdate"
                      | ".lq.NotifyShopUpdate"
                      | ".lq.Lobby.oauth2Auth"
                      | ".lq.Lobby.oauth2Check"
                      | ".lq.NotifyNewMail"
                      | ".lq.Lobby.oauth2Login"
                      | ".lq.Lobby.fetchLastPrivacy"
                      | ".lq.Lobby.fetchServerTime"
                      | ".lq.Lobby.fetchServerSettings"
                      | ".lq.Lobby.fetchConnectionInfo"
                      | ".lq.Lobby.fetchClientValue"
                      | ".lq.Lobby.fetchFriendList"
                      | ".lq.Lobby.fetchFriendApplyList"
                      | ".lq.Lobby.fetchRecentFriend"
                      | ".lq.Lobby.fetchMailInfo"):
                    logger.info(message)
                    continue
                case ".lq.Lobby.fetchDailyTask":
                    logger.info(message)

                    break_ = False
                    while True:
                        next_message = self._db_client.dequeue_message(5)
                        if next_message is None:
                            # If there are no more messages,
                            # the transition to the home screen
                            # has been completed.
                            break_ = True
                            break
                        _, next_name, _, _, _ = next_message
                        if next_name == ".lq.Lobby.heatbeat":
                            # Discard subsequent
                            # '.lq.Lobby.heatbeat' messages.
                            logger.info(next_message)
                            continue
                        # Backfill the prefetched message and
                        # proceed to the next.
                        self._db_client.put_back(next_message)
                        break
                    if break_:
                        break

                    continue
                case (".lq.Lobby.fetchReviveCoinInfo"
                      | ".lq.Lobby.fetchTitleList"
                      | ".lq.Lobby.fetchBagInfo"
                      | ".lq.Lobby.fetchShopInfo"
                      | ".lq.Lobby.fetchShopInterval"
                      | ".lq.Lobby.fetchActivityList"
                      | ".lq.Lobby.fetchAccountActivityData"
                      | ".lq.Lobby.fetchActivityInterval"
                      | ".lq.Lobby.fetchActivityBuff"
                      | ".lq.Lobby.fetchVipReward"
                      | ".lq.Lobby.fetchMonthTicketInfo"
                      | ".lq.Lobby.fetchAchievement"
                      | ".lq.Lobby.fetchSelfGamePointRank"
                      | ".lq.Lobby.fetchCommentSetting"
                      | ".lq.Lobby.fetchAccountSettings"
                      | ".lq.Lobby.fetchModNicknameTime"
                      | ".lq.Lobby.fetchMisc"
                      | ".lq.Lobby.fetchAnnouncement"
                      | ".lq.Lobby.fetchRollingNotice"
                      | ".lq.Lobby.loginSuccess"
                      | ".lq.Lobby.fetchCharacterInfo"
                      | ".lq.Lobby.fetchAllCommonViews"):
                    logger.info(message)
                    continue
                case ".lq.Lobby.loginBeat":
                    logger.info(message)
                    num_login_beats += 1
                    if num_login_beats == 2:  # noqa: PLR2004
                        break
                    continue
                case ".lq.Lobby.fetchCollectedGameRecordList":
                    logger.info(message)
                    continue

            raise InconsistentMessage(str(message), sct)

        while True:
            now = datetime.datetime.now(datetime.UTC)
            message = self._db_client.dequeue_message(0.1)
            if message is None:
                break
            _, name, _, _, _ = message

            match name:
                case ".lq.Lobby.heatbeat":
                    continue
                case ".lq.Lobby.updateClientValue":
                    logger.info(message)
                    continue
                case ".lq.Lobby.fetchDailyTask":
                    logger.info(message)

                    # If there are no more messages,
                    # the transition to the home screen
                    # has been completed.
                    message = self._db_client.dequeue_message(5)
                    if message is None:
                        return

                    # Backfill the prefetched message and
                    # proceed to the next.
                    self._db_client.put_back(message)
                    continue
                case (".lq.NotifyAccountUpdate"
                      | ".lq.NotifyAnnouncementUpdate"
                      | ".lq.Lobby.readAnnouncement"
                      | ".lq.Lobby.doActivitySignIn"):
                    logger.info(message)
                    continue

            raise InconsistentMessage(str(message), sct)

    def create_room(self, timeout: TimeoutType = 60.0) -> None:
        self._assert_not_stale()

        if isinstance(timeout, int | float):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.UTC) + timeout

        # Click "Friendly Match".
        template = Template.open_file("template/home/marker3",
                                      self._browser.zoom_ratio)
        template.click(self._browser)

        # Wait until "Create room" is displayed.
        template = Template.open_file("template/home/create_room",
                                      self._browser.zoom_ratio)
        template.wait_until(self._browser, deadline)

        # Click "Create room"
        template.click(self._browser)

        # Wait until "Create" is displayed.
        template = Template.open_file("template/home/room_creation/create",
                                      self._browser.zoom_ratio)
        template.wait_until(self._browser, deadline)

        # Click "Create"
        template.click(self._browser)

        # Wait until room screen is displayed.
        now = datetime.datetime.now(datetime.UTC)
        RoomHostPresentation._wait(self._browser, deadline - now)  # noqa: SLF001

        now = datetime.datetime.now(datetime.UTC)
        p = RoomHostPresentation._create(  # noqa: SLF001
            self._browser, self._db_client, deadline - now,
        )
        self._set_new_presentation(p)
