"""
Columns of the region, district and school files in the admin's import/export (apps.core.sheets).

A row finds its record by the parent place and the number, or by the name when the number is
empty or new; a found record is updated, otherwise a new one is added. Rows that are not in the
file are left alone: a file never deletes anything.
"""

from import_export import widgets
from import_export.fields import Field

from apps.core.sheets import (
    NumberWidget,
    SheetMeta,
    SheetResource,
    StatusWidget,
    TextWidget,
    cell_text,
    find_existing,
    name_key,
    pick,
)

from .models import District, Region, School

REGION, DISTRICT, NUMBER, NAME, STATUS = "Viloyat", "Tuman", "Raqami", "Nomi", "Faol"

STATUS_HELP = "“ha” yoki “yo‘q”. Bo‘sh qolsa: yangisi faol, borining holati o‘zgarmaydi."


class RegionWidget(widgets.Widget):
    """A region by its number or its name. Loads the regions once per file."""

    def __init__(self):
        super().__init__()
        self._regions = None

    def clean(self, value, row=None, **kwargs):
        if not cell_text(value):
            return None
        if self._regions is None:
            self._regions = list(Region.objects.all())
        return pick(self._regions, value, "viloyat")

    def render(self, value, obj=None, **kwargs):
        return value.name if value else ""


class DistrictWidget(widgets.Widget):
    """A district by its number or name inside the region of the same row's "Viloyat" column."""

    def __init__(self):
        super().__init__()
        self.regions = RegionWidget()
        self._districts: dict[int, list[District]] = {}

    def clean(self, value, row=None, **kwargs):
        if not cell_text(value):
            return None
        region = self.regions.clean((row or {}).get(REGION))
        if region is None:
            raise ValueError("“Viloyat” ustuni bo‘sh: tuman qaysi viloyatdaligini yozing.")
        if region.pk not in self._districts:
            self._districts[region.pk] = list(region.districts.all())
        return pick(self._districts[region.pk], value, f"tuman {region.name}da")

    def render(self, value, obj=None, **kwargs):
        return value.name if value else ""


class RegionResource(SheetResource):
    number = Field(attribute="number", column_name=NUMBER, widget=NumberWidget())
    name = Field(attribute="name", column_name=NAME, widget=TextWidget())
    status = Field(
        attribute="status", column_name=STATUS, widget=StatusWidget(), saves_null_values=False
    )

    required_columns = (NUMBER, NAME)
    column_help = {
        NUMBER: "Viloyat raqami. Shu raqamli viloyat bazada bo‘lsa, u yangilanadi.",
        NAME: "Masalan: Toshkent viloyati.",
        STATUS: STATUS_HELP,
    }
    sample_rows = [
        {NUMBER: 1, NAME: "Qoraqalpog‘iston Respublikasi", STATUS: "ha"},
        {NUMBER: 2, NAME: "Andijon viloyati", STATUS: "ha"},
    ]

    class Meta(SheetMeta):
        model = Region
        fields = ("number", "name", "status")
        import_id_fields = ("number",)

    def get_instance(self, instance_loader, row):
        return find_existing(Region.objects.all(), self.cleaned("number", row), row.get(NAME))

    def row_key(self, instance):
        return instance.number


class DistrictResource(SheetResource):
    region = Field(attribute="region", column_name=REGION, widget=RegionWidget())
    number = Field(attribute="number", column_name=NUMBER, widget=NumberWidget())
    name = Field(attribute="name", column_name=NAME, widget=TextWidget())
    status = Field(
        attribute="status", column_name=STATUS, widget=StatusWidget(), saves_null_values=False
    )

    required_columns = (REGION, NUMBER, NAME)
    column_help = {
        REGION: "Viloyat nomi yoki raqami: “Andijon viloyati” yoki 2.",
        NUMBER: "Tumanning viloyat ichidagi raqami.",
        NAME: "Masalan: Asaka tumani.",
        STATUS: STATUS_HELP,
    }
    sample_rows = [
        {REGION: "Andijon viloyati", NUMBER: 1, NAME: "Andijon shahri", STATUS: "ha"},
        {REGION: 2, NUMBER: 2, NAME: "Asaka tumani", STATUS: "ha"},
    ]

    class Meta(SheetMeta):
        model = District
        fields = ("region", "number", "name", "status")
        import_id_fields = ("region", "number")

    def get_instance(self, instance_loader, row):
        region = self.cleaned("region", row)
        if region is None:
            return None
        return find_existing(region.districts.all(), self.cleaned("number", row), row.get(NAME))

    def row_key(self, instance):
        return (instance.region_id, instance.number)


class SchoolResource(SheetResource):
    # Read on import by the "Tuman" column, which needs it to tell apart same-named districts.
    region = Field(
        attribute="district__region", column_name=REGION, widget=RegionWidget(), readonly=True
    )
    district = Field(attribute="district", column_name=DISTRICT, widget=DistrictWidget())
    number = Field(attribute="number", column_name=NUMBER, widget=NumberWidget())
    name = Field(attribute="name", column_name=NAME, widget=TextWidget())
    status = Field(
        attribute="status", column_name=STATUS, widget=StatusWidget(), saves_null_values=False
    )

    required_columns = (REGION, DISTRICT, NAME)
    column_help = {
        REGION: "Viloyat nomi yoki raqami.",
        DISTRICT: "Tuman nomi yoki raqami (shu viloyat ichida).",
        NUMBER: "Maktab raqami. Ixtisoslashgan maktablar uchun bo‘sh qolishi mumkin.",
        NAME: "Masalan: 12-umumta’lim maktabi.",
        STATUS: STATUS_HELP,
    }
    sample_rows = [
        {
            REGION: "Andijon viloyati",
            DISTRICT: "Asaka tumani",
            NUMBER: 12,
            NAME: "12-umumta’lim maktabi",
            STATUS: "ha",
        },
        {REGION: 2, DISTRICT: 2, NUMBER: "", NAME: "Ixtisoslashtirilgan maktab", STATUS: "ha"},
    ]

    class Meta(SheetMeta):
        model = School
        fields = ("region", "district", "number", "name", "status")
        import_id_fields = ("district", "name")

    def import_columns(self) -> list[str]:
        return [REGION, *super().import_columns()]

    def get_instance(self, instance_loader, row):
        district = self.cleaned("district", row)
        if district is None:
            return None
        return find_existing(district.schools.all(), self.cleaned("number", row), row.get(NAME))

    def row_key(self, instance):
        return (instance.district_id, instance.number or name_key(instance.name))
