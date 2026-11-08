"""Exam assignment: which pupils see which exam (ExamTarget, Exam.objects.visible_to)."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.exams.models import Exam, ExamTarget
from apps.schools.models import Classroom, District, Region, School

from .conftest import client_for, make_classroom, make_exam, make_pupil

pytestmark = pytest.mark.django_db


def visible(pupil) -> list[str]:
    response = client_for(pupil).get("/api/examinations/available")
    assert response.status_code == 200
    return [exam["title"] for exam in response.json()["examinations"]]


@pytest.fixture
def other_place(db):
    """A second region with its own district and school, far away from Aliya."""
    region = Region.objects.create(name="Boshqa viloyat", number=2)
    district = District.objects.create(region=region, name="Boshqa tuman", number=1)
    school = School.objects.create(district=district, name="Uzoq maktab", number=1)
    return region, district, school


class TestWhoSeesTheExam:
    def test_exam_without_targets_is_seen_by_nobody(self, aliya):
        exam = make_exam(targets=[])
        assert visible(aliya) == []
        assert client_for(aliya).post(f"/api/examinations/{exam.pk}/start").status_code == 404

    @pytest.mark.parametrize("level", ["region", "district", "school", "classroom"])
    def test_each_level_of_the_pupils_place_matches(self, aliya, level):
        classroom = aliya.classroom
        place = {
            "region": classroom.school.district.region,
            "district": classroom.school.district,
            "school": classroom.school,
            "classroom": classroom,
        }[level]
        make_exam(targets=[{level: place}])
        assert visible(aliya) == ["Test imtihon"]

    @pytest.mark.parametrize("level", ["region", "district", "school"])
    def test_another_place_does_not_match(self, aliya, other_place, level):
        region, district, school = other_place
        make_exam(
            targets=[{level: {"region": region, "district": district, "school": school}[level]}]
        )
        assert visible(aliya) == []

    def test_another_class_of_the_same_school_does_not_match(self, aliya):
        parallel = make_classroom(number=5, category="B")
        make_exam(targets=[{"classroom": parallel}])
        assert visible(aliya) == []

    def test_grade_alone_means_that_grade_everywhere(self, aliya, other_place):
        make_exam(targets=[{"grade": 5}])
        far_away = make_pupil("33333333333333", "Uzoq")
        far_away.classroom = Classroom.objects.create(school=other_place[2], number=5, category="A")
        far_away.save()
        older = make_pupil("44444444444444", "Katta")
        older.classroom = make_classroom(number=6)
        older.save()
        assert visible(aliya) == visible(far_away) == ["Test imtihon"]
        assert visible(older) == []

    def test_grade_narrows_a_place(self, aliya):
        region = aliya.classroom.school.district.region
        make_exam(title="9-sinflar uchun", targets=[{"region": region, "grade": 9}])
        make_exam(title="5-sinflar uchun", targets=[{"region": region, "grade": 5}])
        assert visible(aliya) == ["5-sinflar uchun"]

    def test_any_matching_target_is_enough(self, aliya, other_place):
        make_exam(targets=[{"region": other_place[0]}, {"school": aliya.classroom.school}])
        assert visible(aliya) == ["Test imtihon"]

    def test_starting_needs_the_exam_to_be_assigned(self, aliya, other_place):
        exam = make_exam(targets=[{"region": other_place[0]}])
        assert client_for(aliya).post(f"/api/examinations/{exam.pk}/start").status_code == 404

    def test_unpublished_exam_stays_hidden_even_when_assigned(self, aliya):
        exam = make_exam()
        Exam.objects.filter(pk=exam.pk).update(is_published=False)
        assert visible(aliya) == []


class TestStartedExamStaysVisible:
    def test_after_targets_change(self, aliya, other_place):
        exam = make_exam()
        client = client_for(aliya)
        assert client.post(f"/api/examinations/{exam.pk}/start").status_code == 201
        exam.targets.update(region=other_place[0])
        assert visible(aliya) == ["Test imtihon"]
        # Starting again returns the running attempt instead of a 404.
        assert client.post(f"/api/examinations/{exam.pk}/start").status_code == 200

    def test_after_the_pupil_moves_to_another_class(self, aliya):
        exam = make_exam(targets=[{"classroom": aliya.classroom}])
        assert client_for(aliya).post(f"/api/examinations/{exam.pk}/start").status_code == 201
        aliya.classroom = make_classroom(number=6, category="A")
        aliya.save()
        assert visible(aliya) == ["Test imtihon"]

    def test_but_not_for_other_pupils(self, aliya, bek):
        exam = make_exam(targets=[{"classroom": aliya.classroom}])
        client_for(aliya).post(f"/api/examinations/{exam.pk}/start")
        exam.targets.all().delete()
        assert visible(bek) == []


class TestTargetRules:
    def make(self, **fields) -> ExamTarget:
        return ExamTarget(exam=make_exam(targets=[]), **fields)

    def test_empty_target_is_rejected(self, db):
        with pytest.raises(ValidationError):
            self.make().full_clean()

    def test_empty_target_is_rejected_by_the_database_too(self, db):
        with pytest.raises(IntegrityError), transaction.atomic():
            self.make().save()

    def test_a_top_down_chain_of_places_keeps_only_the_narrowest(self, db):
        classroom = make_classroom()
        school = classroom.school
        target = self.make(
            region=school.district.region,
            district=school.district,
            school=school,
            classroom=classroom,
        )
        target.full_clean()
        assert (target.region, target.district, target.school) == (None, None, None)
        assert target.classroom == classroom

    def test_places_that_do_not_contain_each_other_are_rejected(self, db, other_place):
        classroom = make_classroom()
        region, district, _school = other_place
        with pytest.raises(ValidationError) as error:
            self.make(region=region, district=district, classroom=classroom).full_clean()
        assert set(error.value.message_dict) == {"region", "district"}
        assert "tanlangan tumanda emas" in error.value.message_dict["district"][0]

    def test_grade_together_with_a_class_is_rejected(self, db):
        with pytest.raises(ValidationError):
            self.make(classroom=make_classroom(), grade=5).full_clean()

    @pytest.mark.parametrize("grade", [0, 12])
    def test_grade_out_of_range_is_rejected(self, db, grade):
        with pytest.raises(ValidationError):
            self.make(grade=grade).full_clean()

    def test_readable_names(self, db):
        classroom = make_classroom()
        region = classroom.school.district.region
        assert str(ExamTarget(grade=9)) == "Barcha 9-sinflar"
        assert str(ExamTarget(region=region, grade=9)) == "Viloyat, 9-sinflar"
        assert str(ExamTarget(classroom=classroom)) == "5-A, 1-maktab (Tuman)"


class TestAdmin:
    @pytest.fixture
    def staff(self, client):
        client.force_login(get_user_model().objects.create_superuser("admin", password="x"))
        return client

    def exam_form(self, **targets) -> dict:
        form = {
            "title": "Admin imtihoni",
            "description": "",
            "duration_minutes": 30,
            "points_per_question": 2,
            "review_enabled": "on",
            "is_published": "on",
            "targets-TOTAL_FORMS": 1,
            "targets-INITIAL_FORMS": 0,
            "targets-MIN_NUM_FORMS": 0,
            "targets-MAX_NUM_FORMS": 1000,
            "sections-TOTAL_FORMS": 0,
            "sections-INITIAL_FORMS": 0,
            "sections-MIN_NUM_FORMS": 0,
            "sections-MAX_NUM_FORMS": 1000,
        }
        for name in ("region", "district", "school", "classroom", "grade"):
            form[f"targets-0-{name}"] = targets.get(name, "")
        return form

    def test_target_is_saved_from_the_exam_page(self, staff):
        classroom = make_classroom()
        response = staff.post("/admin/exams/exam/add/", self.exam_form(school=classroom.school_id))
        assert response.status_code == 302, response.content.decode()[:600]
        assert Exam.objects.get().targets.get().school == classroom.school

    def test_region_district_and_school_in_one_row_are_saved_as_the_school(self, staff, aliya):
        school = aliya.classroom.school
        form = self.exam_form(
            region=school.district.region_id, district=school.district_id, school=school.pk
        )
        response = staff.post("/admin/exams/exam/add/", form)
        assert response.status_code == 302, response.content.decode()[:600]
        target = Exam.objects.get().targets.get()
        assert (target.region, target.district, target.school) == (None, None, school)
        assert Exam.objects.visible_to(
            aliya
        ).exists()  # the API also needs questions, not added here

    def test_a_school_from_another_district_shows_an_error(self, staff, other_place):
        classroom = make_classroom()
        form = self.exam_form(district=other_place[1].pk, school=classroom.school_id)
        response = staff.post("/admin/exams/exam/add/", form)
        assert response.status_code == 200
        assert "tanlangan tumanda emas" in response.content.decode()
        assert not Exam.objects.exists()

    def test_published_exam_without_targets_warns(self, staff):
        response = staff.post("/admin/exams/exam/add/", self.exam_form(), follow=True)
        assert "hech kimga biriktirilmagan" in response.content.decode()

    def test_list_shows_who_takes_the_exam(self, staff):
        make_exam(title="Biriktirilgan", targets=[{"grade": 9}])
        make_exam(title="Biriktirilmagan", targets=[])
        page = staff.get("/admin/exams/exam/").content.decode()
        assert "Barcha 9-sinflar" in page
        assert "Hech kimga (biriktirilmagan)" in page

    def test_classroom_autocomplete_for_targets_works(self, staff):
        make_classroom()
        response = staff.get(
            "/admin/autocomplete/",
            {
                "app_label": "exams",
                "model_name": "examtarget",
                "field_name": "classroom",
                "term": "5-A",
            },
        )
        assert response.status_code == 200
        assert response.json()["results"][0]["text"] == "5-A, 1-maktab (Tuman)"

    def autocomplete(self, staff, field, **parents) -> list[str]:
        params = {"app_label": "exams", "model_name": "examtarget", "field_name": field, **parents}
        response = staff.get("/admin/autocomplete/", params)
        assert response.status_code == 200
        return [result["text"] for result in response.json()["results"]]

    def test_school_list_follows_the_chosen_district(self, staff, other_place):
        here = make_classroom().school
        region, district, far = other_place
        assert len(self.autocomplete(staff, "school")) == 2  # nothing chosen: every school
        assert self.autocomplete(staff, "school", district=district.pk) == [str(far)]
        assert self.autocomplete(staff, "school", district=here.district_id) == [str(here)]
        assert self.autocomplete(staff, "school", region=region.pk) == [str(far)]

    def test_district_and_class_lists_follow_their_parents(self, staff, other_place):
        classroom = make_classroom()
        region, district, far = other_place
        assert self.autocomplete(staff, "district", region=region.pk) == [str(district)]
        assert self.autocomplete(staff, "classroom", school=classroom.school_id) == [str(classroom)]
        assert self.autocomplete(staff, "classroom", school=far.pk) == []

    def test_a_malformed_parent_matches_nothing(self, staff):
        make_classroom()
        assert self.autocomplete(staff, "school", district="abc") == []
