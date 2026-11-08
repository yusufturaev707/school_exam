from datetime import timedelta
from unittest import mock
from uuid import uuid4

import pytest
from django.utils import timezone

from apps.games import services
from apps.games.achievements import achievements_for
from apps.games.models import DailyChallengeCompletion, Game, GameSession
from apps.games.selectors import statistics_for

from .conftest import client_for

pytestmark = pytest.mark.django_db

KEY = {"HTTP_IDEMPOTENCY_KEY": "key-1"}


def game(slug: str) -> Game:
    return Game.objects.get(slug=slug)


def start(api, slug="yashiringan-son", difficulty="easy", daily=False):
    return api.post(
        f"/api/games/{game(slug).pk}/start",
        {"difficulty": difficulty, "daily": daily},
        format="json",
    )


def solve_memory_moves(session: GameSession) -> list[list[str]]:
    by_face: dict[str, list[str]] = {}
    for card in session.content["cards"]:
        by_face.setdefault(card["face"], []).append(card["id"])
    return list(by_face.values())


def complete(api, session_id, body=None):
    return api.post(f"/api/games/sessions/{session_id}/complete", body or {}, format="json", **KEY)


def answer(api, session_id, question_id, option_id):
    return api.post(
        f"/api/games/sessions/{session_id}/answer",
        {"questionId": question_id, "optionId": option_id},
        format="json",
    )


def right_and_wrong(question: dict) -> tuple[str, str]:
    right = question["correct_option_id"]
    return right, next(o["id"] for o in question["options"] if o["id"] != right)


class TestCatalogue:
    def test_seeded_catalogue(self, api):
        games = api.get("/api/games").json()["games"]
        assert len(games) == 7
        assert sum(1 for g in games if g["isActive"]) == 3
        assert games[0]["intro"]["title"]
        assert games[0]["completedCount"] == 0

    def test_catalogue_keeps_admin_order(self, api):
        # Django drops Meta.ordering on GROUP BY queries, and the daily pick relies on this order.
        slugs = [game["slug"] for game in api.get("/api/games").json()["games"]]
        assert slugs[:3] == ["xotira-kartalari", "yashiringan-son", "naqsh-ustasi"]

    def test_categories(self, api):
        categories = api.get("/api/games/categories").json()["categories"]
        assert [c["id"] for c in categories] == [
            "memory",
            "logic",
            "math",
            "attention",
            "spatial",
            "language",
        ]
        math = next(c for c in categories if c["id"] == "math")
        assert (math["gameCount"], math["activeCount"]) == (2, 1)

    def test_detail_by_slug(self, api):
        assert api.get("/api/games/naqsh-ustasi").json()["game"]["kind"] == "pattern"
        response = api.get("/api/games/no-such-game")
        assert (response.status_code, response.json()["code"]) == (404, "GAME_NOT_FOUND")

    def test_completed_count_is_per_pupil(self, api, aliya, bek):
        session = GameSession.objects.get(pk=start(api).json()["session"]["id"])
        complete(api, session.pk)
        slug = session.game.slug
        assert api.get(f"/api/games/{slug}").json()["game"]["completedCount"] == 1
        assert client_for(bek).get(f"/api/games/{slug}").json()["game"]["completedCount"] == 0


class TestStart:
    def test_quiz_content_hides_answers(self, api):
        response = start(api, "yashiringan-son")
        assert response.status_code == 201
        raw = response.content.decode()
        assert "correct_option_id" not in raw
        assert "explanation" not in raw
        content = response.json()["content"]
        assert content["kind"] == "missing-number"
        assert set(content["questions"][0]) == {"id", "sequence", "options"}

    def test_session_totals(self, api):
        session = start(api, "xotira-kartalari", "hard").json()["session"]
        assert session["totalQuestions"] == 8
        assert session["status"] == "in_progress"
        assert session["gameSlug"] == "xotira-kartalari"

    def test_inactive_game(self, api):
        response = start(api, "labirint")
        assert (response.status_code, response.json()["code"]) == (409, "GAME_NOT_AVAILABLE")

    def test_invalid_difficulty(self, api):
        response = start(api, difficulty="impossible")
        assert (response.status_code, response.json()["code"]) == (422, "INVALID_DIFFICULTY")

    def test_body_is_optional(self, api):
        response = api.post(f"/api/games/{game('naqsh-ustasi').pk}/start", {}, format="json")
        assert response.status_code == 201
        assert response.json()["session"]["difficulty"] == "easy"


class TestQuizFlow:
    @pytest.fixture
    def session(self, api) -> GameSession:
        return GameSession.objects.get(pk=start(api).json()["session"]["id"])

    def test_scoring(self, api, session):
        q1, q2 = session.content["questions"][:2]
        body = answer(api, session.pk, q1["id"], right_and_wrong(q1)[0]).json()
        assert (body["correct"], body["score"], body["correctAnswers"]) == (True, 10, 1)
        assert body["explanation"]

        body = answer(api, session.pk, q2["id"], right_and_wrong(q2)[1]).json()
        assert (body["correct"], body["score"]) == (False, 10)
        assert body["correctOptionId"] == q2["correct_option_id"]

    def test_first_answer_counts(self, api, session):
        q = session.content["questions"][0]
        right, wrong = right_and_wrong(q)
        answer(api, session.pk, q["id"], wrong)
        repeat = answer(api, session.pk, q["id"], right).json()
        assert (repeat["correct"], repeat["score"]) == (False, 0)

    def test_invalid_answer(self, api, session):
        response = answer(api, session.pk, "nope", "nope")
        assert (response.status_code, response.json()["code"]) == (422, "INVALID_ANSWER")

    def test_complete_is_idempotent(self, api, session):
        q = session.content["questions"][0]
        answer(api, session.pk, q["id"], right_and_wrong(q)[0])
        first = complete(api, session.pk).json()
        second = complete(api, session.pk).json()
        assert first == second
        assert (first["score"], first["maxScore"], first["bonus"]) == (10, 80, 0)
        assert first["moves"] is None
        assert api.get(f"/api/games/sessions/{session.pk}/result").json() == first

    def test_resume_reveals_only_answered_questions(self, api, session):
        q1 = session.content["questions"][0]
        answer(api, session.pk, q1["id"], right_and_wrong(q1)[1])
        body = api.get(f"/api/games/sessions/{session.pk}").json()
        assert [a["questionId"] for a in body["answers"]] == [q1["id"]]
        assert body["answers"][0]["correctOptionId"] == q1["correct_option_id"]
        assert "correct_option_id" not in str(body["content"])

    def test_result_before_completion(self, api, session):
        response = api.get(f"/api/games/sessions/{session.pk}/result")
        assert (response.status_code, response.json()["code"]) == (409, "SESSION_NOT_COMPLETED")

    def test_abandon_closes_the_session(self, api, session):
        assert api.post(f"/api/games/sessions/{session.pk}/abandon").json()["session"][
            "status"
        ] == ("abandoned")
        assert api.post(f"/api/games/sessions/{session.pk}/abandon").status_code == 200

        q = session.content["questions"][0]
        for response in (
            answer(api, session.pk, q["id"], right_and_wrong(q)[0]),
            complete(api, session.pk),
            api.get(f"/api/games/sessions/{session.pk}"),
        ):
            assert (response.status_code, response.json()["code"]) == (409, "SESSION_ABANDONED")

    def test_abandon_does_not_undo_completion(self, api, session):
        complete(api, session.pk)
        body = api.post(f"/api/games/sessions/{session.pk}/abandon").json()
        assert body["session"]["status"] == "completed"
        response = api.get(f"/api/games/sessions/{session.pk}")
        assert response.json()["code"] == "SESSION_COMPLETED"

    def test_another_pupil_gets_404(self, session, bek):
        intruder = client_for(bek)
        response = intruder.get(f"/api/games/sessions/{session.pk}")
        assert (response.status_code, response.json()["code"]) == (404, "SESSION_NOT_FOUND")
        assert intruder.post(f"/api/games/sessions/{session.pk}/abandon").status_code == 404
        assert complete(intruder, session.pk).status_code == 404
        assert client_for(bek).get(f"/api/games/sessions/{uuid4()}").status_code == 404


class TestMemoryFlow:
    @pytest.fixture
    def session(self, api) -> GameSession:
        return GameSession.objects.get(pk=start(api, "xotira-kartalari").json()["session"]["id"])

    def test_valid_moves_earn_the_score(self, api, session):
        pairs = solve_memory_moves(session)
        body = complete(api, session.pk, {"moves": [[pairs[0][0], pairs[1][0]], *pairs]}).json()
        assert (body["score"], body["correctAnswers"], body["moves"]) == (40, 4, 5)

    @pytest.mark.parametrize(
        "moves",
        [
            None,
            [],
            "win",
            [["c1"]],
            [["c1", "c1"]],
            [["c1", "does-not-exist"]],
            [[1, 2]],
        ],
    )
    def test_claiming_a_win_without_solving_is_rejected(self, api, session, moves):
        response = complete(api, session.pk, {"moves": moves} if moves is not None else {})
        assert (response.status_code, response.json()["code"]) == (422, "INVALID_MOVES")
        session.refresh_from_db()
        assert session.status == "in_progress"

    def test_unsolved_board_is_rejected(self, api, session):
        pairs = solve_memory_moves(session)
        response = complete(api, session.pk, {"moves": pairs[:-1]})
        assert response.json()["code"] == "INVALID_MOVES"

    def test_reusing_a_matched_card_is_rejected(self, api, session):
        pairs = solve_memory_moves(session)
        response = complete(api, session.pk, {"moves": [pairs[0], *pairs]})
        assert response.json()["code"] == "INVALID_MOVES"

    def test_memory_has_no_per_question_answers(self, api, session):
        response = answer(api, session.pk, "x", "y")
        assert (response.status_code, response.json()["code"]) == (400, "ANSWERS_NOT_SUPPORTED")


class TestDailyChallenge:
    def start_todays(self, api):
        today = api.get("/api/games/daily-challenge").json()
        response = api.post(
            f"/api/games/{today['game']['id']}/start",
            {"difficulty": today["difficulty"], "daily": True},
            format="json",
        )
        return GameSession.objects.get(pk=response.json()["session"]["id"])

    def finish(self, api, session):
        body = {}
        if session.content["kind"] == "memory":
            body = {"moves": solve_memory_moves(session)}
        return complete(api, session.pk, body).json()

    def test_bonus_is_granted_once(self, api):
        result = self.finish(api, self.start_todays(api))
        assert result["isDaily"] is True
        assert result["bonus"] == 20
        daily = api.get("/api/games/daily-challenge").json()
        assert daily["completed"] is True
        assert daily["completedAt"].endswith("Z")

        # Once it's earned, a new session isn't a daily one any more.
        assert self.start_todays(api).is_daily is False

    def test_two_parallel_daily_sessions_give_one_bonus(self, api):
        first, second = self.start_todays(api), self.start_todays(api)
        assert first.is_daily and second.is_daily
        bonuses = [self.finish(api, first)["bonus"], self.finish(api, second)["bonus"]]
        assert sorted(bonuses) == [0, 20]
        assert DailyChallengeCompletion.objects.count() == 1

    def test_only_todays_game_and_level_qualify(self, api):
        today = api.get("/api/games/daily-challenge").json()
        other = Game.objects.filter(is_active=True).exclude(pk=today["game"]["id"]).first()
        response = api.post(
            f"/api/games/{other.pk}/start",
            {"difficulty": other.difficulties[0], "daily": True},
            format="json",
        )
        assert response.json()["session"]["isDaily"] is False

    def test_not_requesting_daily_earns_nothing(self, api):
        today = api.get("/api/games/daily-challenge").json()
        response = api.post(
            f"/api/games/{today['game']['id']}/start",
            {"difficulty": today["difficulty"], "daily": False},
            format="json",
        )
        assert response.json()["session"]["isDaily"] is False

    def test_explicit_complete_endpoint(self, api):
        session = self.start_todays(api)
        url = "/api/games/daily-challenge/complete"
        early = api.post(url, {"sessionId": str(session.pk)}, format="json")
        assert (early.status_code, early.json()["code"]) == (409, "NOT_A_COMPLETED_DAILY_SESSION")

        self.finish(api, session)
        body = api.post(url, {"sessionId": str(session.pk)}, format="json").json()
        assert body["completed"] is True

    def test_day_flips_at_tashkent_midnight(self, api):
        # 19:30 UTC is 00:30 the next day in Tashkent.
        moment = timezone.now().replace(hour=19, minute=30, second=0, microsecond=0)
        if moment > timezone.now():
            # A moment in the past: a future one beyond the 8-hour session would log the pupil out.
            moment -= timedelta(days=1)
        with mock.patch("django.utils.timezone.now", return_value=moment):
            date = api.get("/api/games/daily-challenge").json()["date"]
        assert date == str((moment + timedelta(hours=5)).date())


class TestDailyQuestion:
    def test_answer_is_hidden_until_the_pupil_replies(self, api):
        response = api.get("/api/games/daily-question")
        body = response.json()
        assert body["answer"] is None
        assert body["points"] == 5
        assert "correct" not in response.content.decode().lower()
        assert "explanation" not in response.content.decode().lower()

    def test_only_first_answer_counts(self, api, aliya):
        state = services.daily_question_state(aliya)
        question = state.question
        wrong_index = next(
            i for i, label in enumerate(question.options) if label != question.correct_option
        )
        url = "/api/games/daily-question/answer"

        first = api.post(
            url,
            {"questionId": str(question.pk), "optionId": question.option_id(wrong_index)},
            format="json",
        ).json()
        assert first["answer"]["correct"] is False
        assert first["answer"]["pointsEarned"] == 0
        assert first["answer"]["correctOptionId"] == question.correct_option_id

        second = api.post(
            url,
            {"questionId": str(question.pk), "optionId": question.correct_option_id},
            format="json",
        ).json()
        assert second["answer"] == first["answer"]
        assert api.get("/api/games/daily-question").json() == first

    def test_correct_answer_adds_stars(self, api, aliya):
        question = services.daily_question_state(aliya).question
        api.post(
            "/api/games/daily-question/answer",
            {"questionId": str(question.pk), "optionId": question.correct_option_id},
            format="json",
        )
        assert api.get("/api/student/games/statistics").json()["totalScore"] == 5

    def test_invalid_option(self, api):
        response = api.post("/api/games/daily-question/answer", {"optionId": "nope"}, format="json")
        assert (response.status_code, response.json()["code"]) == (422, "INVALID_ANSWER")


class TestAchievements:
    def by_id(self, pupil) -> dict:
        return {a.id: a for a in achievements_for(pupil)}

    def test_new_pupil_has_nothing_unlocked(self, api):
        achievements = api.get("/api/student/achievements").json()["achievements"]
        assert len(achievements) == 7
        assert all(a["unlockedAt"] is None for a in achievements)

    def test_badges_needing_unplayable_games_are_coming_soon(self, aliya):
        items = self.by_id(aliya)
        assert items["attention-champion"].coming_soon is True
        assert items["memory-master"].coming_soon is False

    def test_first_game_unlocks_and_reports_once(self, api, aliya):
        session = GameSession.objects.get(pk=start(api).json()["session"]["id"])
        result = complete(api, session.pk).json()
        assert [a["id"] for a in result["newAchievements"]] == ["first-step"]

        second = GameSession.objects.get(pk=start(api).json()["session"]["id"])
        assert complete(api, second.pk).json()["newAchievements"] == []

    def test_progress_and_unlock_time_of_counting_badge(self, api, aliya):
        finished_at = []
        for _ in range(3):
            session = GameSession.objects.get(pk=start(api).json()["session"]["id"])
            complete(api, session.pk)
            session.refresh_from_db()
            finished_at.append(session.completed_at)
            if len(finished_at) == 2:
                badge = self.by_id(aliya)["math-explorer"]
                assert (badge.progress_current, badge.unlocked_at) == (2, None)

        badge = self.by_id(aliya)["math-explorer"]
        assert (badge.progress_current, badge.progress_target) == (3, 3)
        assert badge.unlocked_at == finished_at[2]

    def test_trying_three_categories_unlocks_curious_mind(self, api, aliya):
        for slug in ("yashiringan-son", "naqsh-ustasi"):
            session = GameSession.objects.get(pk=start(api, slug).json()["session"]["id"])
            complete(api, session.pk)
        assert self.by_id(aliya)["curious-mind"].unlocked_at is None

        memory = GameSession.objects.get(pk=start(api, "xotira-kartalari").json()["session"]["id"])
        complete(api, memory.pk, {"moves": solve_memory_moves(memory)})
        assert self.by_id(aliya)["curious-mind"].unlocked_at is not None


class TestStatisticsAndCleanup:
    def test_statistics(self, api, aliya):
        session = GameSession.objects.get(pk=start(api).json()["session"]["id"])
        q = session.content["questions"][0]
        answer(api, session.pk, q["id"], right_and_wrong(q)[0])
        complete(api, session.pk)
        start(api)  # unfinished sessions must not count

        body = api.get("/api/student/games/statistics").json()
        assert (body["totalCompleted"], body["totalScore"]) == (1, 10)
        assert {c["category"]: c["completed"] for c in body["categories"]}["math"] == 1
        played = next(g for g in body["games"] if g["slug"] == "yashiringan-son")
        assert (played["completed"], played["bestScore"], played["maxScore"]) == (1, 10, 80)
        untouched = next(g for g in body["games"] if g["slug"] == "naqsh-ustasi")
        assert untouched["bestScore"] is None
        assert body["recent"][0]["sessionId"] == str(session.pk)

    def test_statistics_are_per_pupil(self, api, bek):
        session = GameSession.objects.get(pk=start(api).json()["session"]["id"])
        complete(api, session.pk)
        assert statistics_for(bek)["total_completed"] == 0

    def test_purge_keeps_completed_and_recent_sessions(self, api):
        old = timezone.now() - timedelta(days=2)
        completed = GameSession.objects.get(pk=start(api).json()["session"]["id"])
        complete(api, completed.pk)
        stale = GameSession.objects.get(pk=start(api).json()["session"]["id"])
        recent = GameSession.objects.get(pk=start(api).json()["session"]["id"])
        GameSession.objects.filter(pk__in=[completed.pk, stale.pk]).update(started_at=old)

        services.purge_stale_sessions()

        remaining = set(GameSession.objects.values_list("pk", flat=True))
        assert remaining == {completed.pk, recent.pk}


def test_game_without_a_generator_cannot_be_activated(db):
    from django.core.exceptions import ValidationError

    maze = Game.objects.get(slug="labirint")
    maze.is_active = True
    with pytest.raises(ValidationError):
        maze.full_clean()
