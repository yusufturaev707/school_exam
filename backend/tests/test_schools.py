"""The Region -> District -> School -> Classroom -> Pupil structure and how it affects pupils."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from apps.accounts.models import Pupil
from apps.accounts.services import authenticate_by_qr, issue_qr_token
from apps.core.exceptions import ApiError
from apps.schools.models import Classroom, District, Region, School

from .conftest import ALIYA_JSHSHIR, client_for, make_classroom

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff(client):
    client.force_login(get_user_model().objects.create_superuser("admin", password="x"))
    return client


def login(jshshir=ALIYA_JSHSHIR):
    return client_for().post("/api/auth/jshshir", {"jshshir": jshshir}, format="json")


class TestStructure:
    def test_classroom_name_is_generated_and_letter_normalised(self):
        school = make_classroom().school
        classroom = Classroom.objects.create(school=school, number=7, category=" v ")
        assert (classroom.name, classroom.category) == ("7-V", "V")

    def test_explicit_classroom_name_is_kept(self):
        school = make_classroom().school
        classroom = Classroom.objects.create(school=school, number=9, category="A", name="9-IT")
        assert classroom.name == "9-IT"

    def test_same_class_can_not_exist_twice_in_a_school(self):
        classroom = make_classroom()
        with pytest.raises(IntegrityError), transaction.atomic():
            Classroom.objects.create(school=classroom.school, number=5, category="A")

    def test_same_class_can_exist_in_another_school(self):
        make_classroom(school_number=1)
        make_classroom(school_number=2)
        assert Classroom.objects.count() == 2

    def test_schools_without_a_number_do_not_collide(self):
        district = make_classroom().school.district
        School.objects.create(district=district, name="Ixtisoslashgan maktab")
        School.objects.create(district=district, name="Prezident maktabi")
        assert School.objects.filter(number=None).count() == 2

    def test_same_district_name_is_allowed_in_another_region(self):
        other = Region.objects.create(name="Boshqa", number=99)
        District.objects.create(region=other, name="Tuman", number=1)
        make_classroom()
        assert District.objects.filter(name="Tuman").count() == 2

    @pytest.mark.parametrize("level", ["classroom", "school", "district", "region"])
    def test_nothing_with_pupils_under_it_can_be_deleted(self, aliya, level):
        classroom = aliya.classroom
        target = {
            "classroom": classroom,
            "school": classroom.school,
            "district": classroom.school.district,
            "region": classroom.school.district.region,
        }[level]
        with pytest.raises(ProtectedError):
            target.delete()
        assert Pupil.objects.filter(pk=aliya.pk).exists()


class TestStatusWorksDownwards:
    def switch_off(self, aliya, level):
        classroom = aliya.classroom
        school = classroom.school
        district = school.district
        target = {
            "pupil": aliya,
            "classroom": classroom,
            "school": school,
            "district": district,
            "region": district.region,
        }[level]
        target.status = False
        target.save()

    @pytest.mark.parametrize("level", ["pupil", "classroom", "school", "district", "region"])
    def test_login_is_refused(self, aliya, level):
        self.switch_off(aliya, level)
        response = login()
        assert (response.status_code, response.json()["code"]) == (401, "INVALID_CREDENTIALS")

    @pytest.mark.parametrize("level", ["pupil", "classroom", "school", "district", "region"])
    def test_running_session_ends(self, aliya, level):
        client = client_for(aliya)
        assert client.get("/api/auth/me").status_code == 200
        self.switch_off(aliya, level)
        assert client.get("/api/auth/me").status_code == 401

    @pytest.mark.parametrize("level", ["pupil", "school", "region"])
    def test_qr_is_refused_and_not_consumed(self, aliya, level):
        token, entry = issue_qr_token(aliya)
        self.switch_off(aliya, level)
        with pytest.raises(ApiError) as error:
            authenticate_by_qr(token)
        assert error.value.code == "QR_INVALID"
        entry.refresh_from_db()
        assert entry.used_at is None


class TestApi:
    def test_class_and_school_come_from_the_structure(self, aliya):
        student = login().json()["student"]
        assert student["className"] == "5-A"
        assert student["schoolName"] == "1-maktab"
        assert "middleName" not in student and "imie" not in str(student).lower()

    def test_me_uses_few_queries(self, aliya, django_assert_max_num_queries):
        client = client_for(aliya)
        with django_assert_max_num_queries(
            2
        ):  # the session and the pupil with its class and school
            assert client.get("/api/auth/me").status_code == 200


class TestAdmin:
    def test_a_whole_class_list_can_be_added_on_the_classroom_page(self, staff):
        classroom = make_classroom()
        form = {
            "school": classroom.school_id,
            "number": classroom.number,
            "category": classroom.category,
            "name": classroom.name,
            "count": 2,
            "status": "on",
            "pupils-TOTAL_FORMS": 2,
            "pupils-INITIAL_FORMS": 0,
            "pupils-MIN_NUM_FORMS": 0,
            "pupils-MAX_NUM_FORMS": 1000,
        }
        for index, (last, first, imie) in enumerate(
            [("Ali", "Vali", "33333333333333"), ("Sobirova", "Nodira", "44444444444444")]
        ):
            form |= {
                f"pupils-{index}-last_name": last,
                f"pupils-{index}-first_name": first,
                f"pupils-{index}-middle_name": "",
                f"pupils-{index}-imie": imie,
                f"pupils-{index}-status": "on",
            }
        response = staff.post(f"/admin/schools/classroom/{classroom.pk}/change/", form)
        assert response.status_code == 302, response.content.decode()[:800]
        assert classroom.pupils.count() == 2
        assert login("33333333333333").status_code == 200

    def test_classroom_list_shows_planned_and_real_counts(self, staff, aliya):
        Classroom.objects.filter(pk=aliya.classroom_id).update(count=25)
        page = staff.get("/admin/schools/classroom/").content.decode()
        assert '<td class="field-count">25</td>' in page
        assert '<td class="field-pupil_count">1</td>' in page

    def test_filters_open_level_by_level(self, staff, aliya):
        classroom = aliya.classroom
        school = classroom.school
        district = school.district
        url = "/admin/accounts/pupil/"

        page = staff.get(url).content.decode()
        assert district.region.name in page
        assert f"?district={district.pk}" not in page

        page = staff.get(url, {"region": district.region_id}).content.decode()
        assert f"district={district.pk}" in page
        assert f"school={school.pk}" not in page

        page = staff.get(url, {"district": district.pk}).content.decode()
        assert f"school={school.pk}" in page

        page = staff.get(url, {"school": school.pk}).content.decode()
        assert f"classroom={classroom.pk}" in page

    def test_filter_narrows_the_list(self, staff, aliya):
        other = make_classroom(school_number=2)
        pupil = Pupil(classroom=other, first_name="Boshqa", last_name="Maktabdan")
        pupil.set_imie("66666666666666")
        pupil.save()

        page = staff.get("/admin/accounts/pupil/", {"school": other.school_id}).content.decode()
        assert "Maktabdan" in page
        assert "Aliya" not in page

    @pytest.mark.parametrize("param", ["region", "district", "school", "classroom"])
    def test_broken_filter_value_is_not_a_server_error(self, staff, aliya, param):
        response = staff.get("/admin/accounts/pupil/", {param: "abc"})
        assert response.status_code == 200

    def test_choosing_a_new_region_forgets_the_old_district(self, staff, aliya):
        district = aliya.classroom.school.district
        other = Region.objects.create(name="Boshqa viloyat", number=77)
        page = staff.get(
            "/admin/accounts/pupil/", {"region": district.region_id, "district": district.pk}
        ).content.decode()
        assert f"?region={other.pk}&amp;district" not in page
        assert f"?region={other.pk}" in page

    def test_results_can_be_filtered_by_school(self, staff):
        page = staff.get("/admin/exams/examresult/")
        assert page.status_code == 200
