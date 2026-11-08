from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import ApiError
from apps.core.serializers import iso_utc, parse_body
from apps.core.views import require_idempotency_key

from . import selectors, serializers, services
from .achievements import achievements_for


class GameListView(APIView):
    def get(self, request):
        games = services.games_with_counts(request.user)
        return Response({"games": serializers.GameSerializer(games, many=True).data})


class CategoryListView(APIView):
    def get(self, request):
        categories = selectors.categories_info()
        return Response({"categories": serializers.CategorySerializer(categories, many=True).data})


class GameDetailView(APIView):
    def get(self, request, slug):
        game = services.games_with_counts(request.user).filter(slug=slug).first()
        if game is None:
            raise ApiError(404, "GAME_NOT_FOUND")
        return Response({"game": serializers.GameSerializer(game).data})


class StartGameView(APIView):
    def post(self, request, game_id):
        data = parse_body(serializers.StartGameSerializer, request)
        session = services.start_game(request.user, game_id, data.get("difficulty"), data["daily"])
        return Response(serializers.StartedGameSerializer(session).data, status=201)


class SessionDetailView(APIView):
    def get(self, request, session_id):
        session = services.resumable_session(request.user, session_id)
        return Response(serializers.ResumedGameSerializer(session).data)


class AnswerQuestionView(APIView):
    def post(self, request, session_id):
        data = parse_body(serializers.AnswerSerializer, request)
        verdict = services.answer_question(
            request.user, session_id, data["questionId"], data["optionId"]
        )
        return Response(serializers.AnswerVerdictSerializer(verdict).data)


class CompleteGameView(APIView):
    def post(self, request, session_id):
        require_idempotency_key(request)
        data = parse_body(serializers.CompleteGameSerializer, request)
        session = services.complete_game(request.user, session_id, data["moves"])
        return Response(serializers.GameResultSerializer(session).data)


class AbandonGameView(APIView):
    def post(self, request, session_id):
        session = services.abandon_game(request.user, session_id)
        return Response({"session": serializers.GameSessionSerializer(session).data})


class GameResultView(APIView):
    def get(self, request, session_id):
        session = services.finished_session(request.user, session_id)
        return Response(serializers.GameResultSerializer(session).data)


class DailyChallengeView(APIView):
    def get(self, request):
        challenge = services.daily_challenge(request.user)
        return Response(serializers.DailyChallengeSerializer(challenge).data)


class ConfirmDailyChallengeView(APIView):
    def post(self, request):
        data = parse_body(serializers.ConfirmDailySerializer, request)
        completion = services.confirm_daily_challenge(request.user, data["sessionId"])
        return Response(
            {
                "date": str(completion.date),
                "completed": True,
                "completedAt": iso_utc(completion.completed_at),
            }
        )


class DailyQuestionView(APIView):
    def get(self, request):
        state = services.daily_question_state(request.user)
        return Response(serializers.DailyQuestionStateSerializer(state).data)


class AnswerDailyQuestionView(APIView):
    def post(self, request):
        data = parse_body(serializers.DailyAnswerSerializer, request)
        state = services.answer_daily_question(
            request.user, data.get("questionId"), data["optionId"]
        )
        return Response(serializers.DailyQuestionStateSerializer(state).data)


class StatisticsView(APIView):
    def get(self, request):
        stats = selectors.statistics_for(request.user)
        return Response(serializers.StatisticsSerializer(stats).data)


class AchievementListView(APIView):
    def get(self, request):
        achievements = achievements_for(request.user)
        return Response(
            {"achievements": serializers.AchievementSerializer(achievements, many=True).data}
        )
