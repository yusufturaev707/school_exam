"""
The yearly promotion: every class of a school moves up one grade, and the final grade graduates.

The classes themselves move ("5-A" becomes "6-A" with the same pupils), not the pupils. So a class
keeps its pupil list, and nobody has to re-enter thousands of children every September.
"""

import re
from dataclasses import dataclass

from django.db import transaction

from .models import FINAL_GRADE, Classroom, School


class PromotionError(Exception):
    pass


@dataclass(frozen=True)
class PromotionResult:
    promoted: int
    graduated: int


def promote_school(school_id: int, year: int) -> PromotionResult:
    with transaction.atomic():
        # The row lock makes two clicks, or two admins, run one after another. The second one
        # then sees last_promoted_year and stops, instead of moving the children a second grade.
        school = School.objects.select_for_update().get(pk=school_id)
        if school.last_promoted_year == year:
            raise PromotionError(f"{school}: {year}-yilda allaqachon o‘tkazilgan.")

        # Highest grade first. The 11th grade leaves before the 10th takes its place, and so on,
        # so "unique class in a school" is never broken in between.
        classrooms = school.classrooms.current().select_for_update().order_by("-number")
        promoted = graduated = 0
        for classroom in classrooms:
            if classroom.number >= FINAL_GRADE:
                _graduate(classroom, year)
                graduated += 1
            else:
                _move_up(classroom)
                promoted += 1

        school.last_promoted_year = year
        school.save(update_fields=["last_promoted_year"])
    return PromotionResult(promoted=promoted, graduated=graduated)


def _graduate(classroom: Classroom, year: int) -> None:
    # status=False is what actually stops the pupils from logging in (see PupilQuerySet.active).
    classroom.graduated_year = year
    classroom.status = False
    classroom.save(update_fields=["graduated_year", "status"])


def _move_up(classroom: Classroom) -> None:
    old = classroom.number
    classroom.number = old + 1
    # "5-A" -> "6-A" and "5-A (IT)" -> "6-A (IT)". A name that doesn't start with the grade
    # was written by hand, so it is left alone.
    classroom.name = re.sub(rf"^{old}(?!\d)", str(classroom.number), classroom.name)
    classroom.save(update_fields=["number", "name"])
