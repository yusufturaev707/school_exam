"""
Sidebar filters for the admin: Region -> District -> School -> Classroom.

The country has thousands of schools, so a plain `list_filter` would print them all in the sidebar.
Here each level appears only after its parent is chosen, and shows only that parent's children.
"""

from django.contrib import admin

from .models import Classroom, District, Region, School

# Top to bottom: (URL parameter, title, model, field on the model that points to the parent level)
LEVELS = [
    ("region", "Viloyat", Region, None),
    ("district", "Tuman", District, "region"),
    ("school", "Maktab", School, "district"),
    ("classroom", "Sinf", Classroom, "school"),
]


def _make_filter(level: int, lookup: str) -> type[admin.SimpleListFilter]:
    param, label, model, parent_field = LEVELS[level]
    parent_param = LEVELS[level - 1][0] if level > 0 else None
    lower_params = [row[0] for row in LEVELS[level + 1 :]]

    class HierarchyFilter(admin.SimpleListFilter):
        title = label
        parameter_name = param

        def lookups(self, request, model_admin):
            own_value = request.GET.get(param, "")
            parent_value = request.GET.get(parent_param, "") if parent_param else ""
            if parent_param is None:
                options = model.objects.all()
            elif parent_value.isdigit():
                options = model.objects.filter(**{parent_field: parent_value})
            elif own_value.isdigit():
                # Opened from a saved link without the parent. Django skips a filter that has no
                # options, which would quietly show pupils of every school, so keep this one.
                options = model.objects.filter(pk=own_value)
            else:
                return []  # nothing chosen yet, so this level stays hidden
            return [(option.pk, _title(option)) for option in options]

        def queryset(self, request, queryset):
            value = self.value()
            if not value:
                return queryset
            # A broken value in the URL shows an empty list instead of a server error.
            return queryset.filter(**{lookup: value}) if value.isdigit() else queryset.none()

        def choices(self, changelist):
            # Picking a new region must also forget the district chosen under the old one.
            yield {
                "selected": self.value() is None,
                "query_string": changelist.get_query_string(remove=[param, *lower_params]),
                "display": "Hammasi",
            }
            for value, title in self.lookup_choices:
                yield {
                    "selected": self.value() == str(value),
                    "query_string": changelist.get_query_string(
                        {param: value}, remove=lower_params
                    ),
                    "display": title,
                }

    return HierarchyFilter


def hierarchy_filters(*lookups: str) -> list[type[admin.SimpleListFilter]]:
    """
    Pass one ORM path per level, starting from Region, for example:
    `hierarchy_filters("school__district__region", "school__district", "school")`
    """
    return [_make_filter(level, lookup) for level, lookup in enumerate(lookups)]


def _title(option) -> str:
    # After a promotion a school has the new 11-A and last year's graduated 11-A.
    graduated = getattr(option, "graduated_year", None)
    return f"{option.name} ({graduated} bitiruvchilari)" if graduated else option.name


def graduated_filter(lookup: str) -> type[admin.SimpleListFilter]:
    """
    Hides graduated classes (and their pupils) unless asked for: after a few years they would
    outnumber the children who actually study at the school. `lookup` is the path to the
    classroom's `graduated_year`, e.g. "classroom__graduated_year".
    """

    class GraduatedFilter(admin.SimpleListFilter):
        title = "o‘qish holati"
        parameter_name = "graduated"

        def lookups(self, request, model_admin):
            return [("no", "O‘qiyotganlar"), ("yes", "Bitirganlar"), ("all", "Hammasi")]

        def queryset(self, request, queryset):
            value = self.value() or "no"
            if value == "all":
                return queryset
            return queryset.filter(**{f"{lookup}__isnull": value == "no"})

        def choices(self, changelist):
            current = self.value() or "no"
            for value, title in self.lookup_choices:
                yield {
                    "selected": current == value,
                    "query_string": changelist.get_query_string({self.parameter_name: value}),
                    "display": title,
                }

    return GraduatedFilter
