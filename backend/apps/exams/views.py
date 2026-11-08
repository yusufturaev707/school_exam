"""Views stay thin: validate input, call a service or selector, serialize the output."""

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.serializers import parse_body
from apps.core.views import require_idempotency_key

from . import selectors, serializers, services


class AvailableExamsView(APIView):
    def get(self, request):
        summaries = selectors.exam_summaries(request.user)
        return Response(
            {"examinations": serializers.ExamSummarySerializer(summaries, many=True).data}
        )


class StartAttemptView(APIView):
    def post(self, request, exam_id):
        attempt, created = services.start_attempt(request.user, exam_id)
        return Response({"attemptId": str(attempt.pk)}, status=201 if created else 200)


class AttemptDetailView(APIView):
    def get(self, request, attempt_id):
        # Questions carry their pictures inline and don't change during an attempt, so the client
        # loads them once and afterwards asks with ?questions=0 for the small part that does.
        with_questions = request.query_params.get("questions") != "0"
        session = selectors.attempt_session(request.user, attempt_id, with_questions)
        serializer = (
            serializers.AttemptSessionSerializer
            if with_questions
            else serializers.AttemptStateSerializer
        )
        return Response(serializer(session).data)


class SaveAnswerView(APIView):
    def put(self, request, attempt_id, question_id):
        data = parse_body(serializers.SaveAnswerSerializer, request)
        answer = services.save_answer(
            request.user, attempt_id, question_id, data["selectedOptionIds"], data["clientSeq"]
        )
        return Response(serializers.SavedAnswerSerializer(answer).data)


class SubmitAttemptView(APIView):
    def post(self, request, attempt_id):
        require_idempotency_key(request)
        data = parse_body(serializers.SubmitSerializer, request)
        attempt = services.submit_attempt(
            request.user, attempt_id, data["reason"], data["unsavedAnswers"]
        )
        return Response(serializers.SubmitResultSerializer(attempt).data)


class DashboardView(APIView):
    def get(self, request):
        return Response(serializers.DashboardSerializer(selectors.dashboard_for(request.user)).data)


class ResultListView(APIView):
    def get(self, request):
        results = selectors.results_for(request.user)
        return Response({"results": serializers.ResultSummarySerializer(results, many=True).data})


class ResultDetailView(APIView):
    def get(self, request, result_id):
        result = selectors.result_for(request.user, result_id)
        return Response(serializers.ExamResultSerializer(result).data)
