from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from .models import Digimon, Skill


class SkillInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        active_forms = [
            form for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False)
        ]

        if not (1 <= len(active_forms) <= 4):
            raise ValidationError(
                "Her Digimon en az 1, en fazla 4 adet skill sahibi olabilir."
            )


class SkillInline(admin.TabularInline):
    model = Skill
    formset = SkillInlineFormSet
    extra = 1       # Yeni Digimon eklerken hazır 1 boş skill satırı gösterir
    min_num = 1     # Admin formunda minimum 1 skill zorunluluğu
    max_num = 4     # Admin formunda maksimum 4 skill sınırı
    fields = ("skill_name", "skill_attr", "skill_damage", "skill_effect")


@admin.register(Digimon)
class DigimonAdmin(admin.ModelAdmin):
    inlines = [SkillInline]
    list_display = ("id", "name", "attr", "element", "stage", "rank", "role", "skill_count")
    list_filter = ("attr", "element", "stage", "rank", "role")
    search_fields = ("name", "element", "stage")
    ordering = ("id",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related("skills")

    @admin.display(description="Skill Sayısı")
    def skill_count(self, obj):
        return obj.skills.count()


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("id", "skill_name", "digimon", "skill_attr", "skill_damage", "skill_effect")
    list_filter = ("skill_attr",)
    search_fields = ("skill_name", "digimon__name", "skill_effect")
    autocomplete_fields = ("digimon",)