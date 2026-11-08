"""The yearly promotion: classes move up a grade, the final grade graduates (schools.services)."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import Pupil
from apps.schools.models import Classroom, School
from apps.schools.services import PromotionError, promote_school

from .conftest import client_for, make_classroom, make_exam, make_pupil

pytestmark = pytest.mark.django_db
YEAR = 2026


def classes(school: School) -> list[tuple[str, int, bool, int | None]]:
    return list(
        school.classrooms.order_by("number", "category", "graduated_year").values_list(
            "name", "number", "status", "graduated_year"
        )
    )


@pytest.fixture
def school(db) -> School:
    """5-A (with Aliya), 10-A, 11-A and 11-B, the last two graduating this year."""
    for number, category in [(5, "A"), (10, "A"), (11, "A"), (11, "B")]:
        make_classroom(number=number, category=category)
    return School.objects.get()


class TestPromotion:
    def test_every_class_moves_up_and_the_final_grade_graduates(self, school):
        result = promote_school(school.pk, YEAR)
        assert (result.promoted, result.graduated) == (2, 2)
        assert classes(school) == [
            ("6-A", 6, True, None),
            ("11-A", 11, False, YEAR),
            ("11-A", 11, True, None),  # last year's 10-A, next to the graduated 11-A
            ("11-B", 11, False, YEAR),
        ]

    def test_pupils_move_with_their_class(self, school, aliya):
        promote_school(school.pk, YEAR)
        aliya.refresh_from_db()
        assert aliya.classroom.name == "6-A"
        login = client_for().post("/api/auth/jshshir", {"jshshir": "11111111111111"}, format="json")
        assert login.json()["student"]["className"] == "6-A"

    def test_graduates_can_no_longer_log_in(self, school):
        graduate = make_pupil("55555555555555", "Bitiruvchi")
        graduate.classroom = Classroom.objects.get(number=11, category="A")
        graduate.save()
        client = client_for(graduate)
        assert client.get("/api/auth/me").status_code == 200

        promote_school(school.pk, YEAR)
        assert client.get("/api/auth/me").status_code == 401
        assert Pupil.objects.filter(pk=graduate.pk).exists()  # kept, with their results

    def test_switching_a_graduated_class_back_on_still_does_not_let_pupils_in(self, school):
        graduate = make_pupil("55555555555555", "Bitiruvchi")
        graduate.classroom = Classroom.objects.get(number=11, category="A")
        graduate.save()
        promote_school(school.pk, YEAR)
        Classroom.objects.filter(graduated_year=YEAR).update(status=True)
        assert client_for(graduate).get("/api/auth/me").status_code == 401

    def test_second_promotion_in_the_same_year_is_refused(self, school):
        promote_school(school.pk, YEAR)
        with pytest.raises(PromotionError):
            promote_school(school.pk, YEAR)
        assert Classroom.objects.get(name="6-A")  # still 6-A, not 7-A

    def test_next_year_works_and_old_graduates_stay_where_they_are(self, school):
        promote_school(school.pk, YEAR)
        promote_school(school.pk, YEAR + 1)
        assert classes(school) == [
            ("7-A", 7, True, None),
            ("11-A", 11, False, YEAR),
            ("11-A", 11, False, YEAR + 1),
            ("11-B", 11, False, YEAR),
        ]

    def test_custom_names_follow_the_grade_only_when_they_start_with_it(self, school):
        Classroom.objects.filter(number=5).update(name="5-A (IT)")
        make_classroom(number=7, category="B")
        Classroom.objects.filter(number=7).update(name="Prezident sinfi")
        promote_school(school.pk, YEAR)
        names = set(school.classrooms.current().values_list("name", flat=True))
        assert {"6-A (IT)", "Prezident sinfi"} <= names

    def test_inactive_classes_also_move_up(self, school):
        Classroom.objects.filter(number=5).update(status=False)
        promote_school(school.pk, YEAR)
        assert Classroom.objects.get(number=6).status is False

    def test_other_schools_are_not_touched(self, school):
        other = make_classroom(school_number=2, number=5)
        promote_school(school.pk, YEAR)
        other.refresh_from_db()
        assert other.number == 5

    def test_a_new_class_with_a_graduated_name_can_be_created(self, school):
        promote_school(school.pk, YEAR)
        classroom = Classroom(school=school, number=11, category="B")
        classroom.full_clean()
        classroom.save()

    def test_but_a_duplicate_of_a_current_class_is_still_rejected(self, school):
        with pytest.raises(ValidationError):
            Classroom(school=school, number=5, category="A").full_clean()

    def test_exam_for_a_grade_follows_the_new_grade(self, school, aliya):
        make_exam(title="6-sinflar", targets=[{"grade": 6}])
        client = client_for(aliya)
        assert client.get("/api/examinations/available").json()["examinations"] == []
        promote_school(school.pk, YEAR)
        titles = [
            e["title"] for e in client.get("/api/examinations/available").json()["examinations"]
        ]
        assert titles == ["6-sinflar"]


class TestClassroomRules:
    @pytest.mark.parametrize("category", ["А", "5", "ABCD", ""])  # the first is a Cyrillic А
    def test_bad_letters_are_rejected(self, db, category):
        school = make_classroom().school
        with pytest.raises(ValidationError):
            Classroom(school=school, number=6, category=category).full_clean()

    def test_grade_above_the_final_one_is_rejected(self, db):
        school = make_classroom().school
        with pytest.raises(ValidationError):
            Classroom(school=school, number=12, category="A").full_clean()


class TestAdminAction:
    @pytest.fixture
    def staff(self, client):
        client.force_login(get_user_model().objects.create_superuser("admin", password="x"))
        return client

    def post_action(self, staff, school_ids, **extra):
        data = {"action": "promote_to_next_year", "_selected_action": school_ids, **extra}
        return staff.post("/admin/schools/school/", data)

    def test_first_step_only_shows_what_will_happen(self, staff, school, aliya):
        response = self.post_action(staff, [school.pk], index=0)
        page = response.content.decode()
        assert response.status_code == 200
        assert "Bu amalni bekor qilib bo‘lmaydi" in page
        # 5-A and 10-A move, 11-A/B leave
        assert '<td class="num">2</td><td class="num">2 (0 o‘quvchi)</td>' in page
        assert classes(school)[0][0] == "5-A"

    def test_confirming_promotes(self, staff, school):
        response = self.post_action(staff, [school.pk], confirm="yes")
        assert response.status_code == 302
        school.refresh_from_db()
        assert school.last_promoted_year == timezone.localdate().year
        assert classes(school)[0][0] == "6-A"

    def test_select_all_promotes_every_school_in_the_filtered_list(self, staff, school):
        second = make_classroom(school_number=2, number=3).school
        response = self.post_action(staff, [school.pk], confirm="yes", select_across="1")
        assert response.status_code == 302
        assert Classroom.objects.get(school=second).number == 4

    def test_school_already_promoted_this_year_is_skipped_with_a_warning(self, staff, school):
        School.objects.filter(pk=school.pk).update(last_promoted_year=timezone.localdate().year)
        page = self.post_action(staff, [school.pk], index=0).content.decode()
        assert "allaqachon o‘tkazilgan" in page
        # Totals count only the schools that will move, here none.
        assert 'data-stat="moving">0<' in page
        response = self.post_action(staff, [school.pk], confirm="yes")
        assert response.status_code == 302
        assert classes(school)[0][0] == "5-A"

    def test_needs_permission_to_change_classes(self, client, school):
        user = get_user_model().objects.create_user("viewer", password="x", is_staff=True)
        user.user_permissions.add(
            *Permission.objects.filter(codename__in=["view_school", "change_school"])
        )
        client.force_login(user)
        page = client.get("/admin/schools/school/").content.decode()
        assert "promote_to_next_year" not in page

    def test_school_page_hides_graduated_classes(self, staff, school):
        promote_school(school.pk, YEAR)
        page = staff.get(f"/admin/schools/school/{school.pk}/change/").content.decode()
        assert 'name="classrooms-INITIAL_FORMS" value="2"' in page

    def test_classroom_list_hides_graduates_until_asked(self, staff, school):
        promote_school(school.pk, YEAR)
        url = "/admin/schools/classroom/"
        assert "11-B" not in staff.get(url).content.decode()
        assert "11-B" in staff.get(url, {"graduated": "yes"}).content.decode()
