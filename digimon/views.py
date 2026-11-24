# digimon/views.py
import json
from urllib.parse import unquote

from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    AttributeChoices,
    Digimon,
    RankChoices,
    RoleChoices,
    ElementChoices,
    StageChoices,
    FamilyChoices,
)
from .serializers import DigimonSerializer, _normalize_family_list


class DigimonViewSet(viewsets.ModelViewSet):
    serializer_class = DigimonSerializer

    def get_queryset(self):
        queryset = Digimon.objects.prefetch_related("skills").order_by("id")
        params = self.request.query_params

        filter_fields = ("attr", "element", "stage", "rank", "role")
        for field in filter_fields:
            val = params.get(field)
            if val:
                queryset = queryset.filter(**{f"{field}__iexact": val.strip()})

        search = params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search.strip())

        return queryset


def _split_csv(raw_value: str) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _extract_digimon_payload(request) -> dict:
    skill_names = request.POST.getlist("skill_name")
    skill_attrs = request.POST.getlist("skill_attr")
    skill_damages = request.POST.getlist("skill_damage")
    skill_effects = request.POST.getlist("skill_effect")

    skills = []
    for name, attr, damage, effect in zip(
        skill_names, skill_attrs, skill_damages, skill_effects
    ):
        if not any([name.strip(), damage.strip(), effect.strip()]):
            continue
        skills.append({
            "skill_name": name.strip(),
            "skill_attr": attr.strip(),
            "skill_damage": damage.strip(),
            "skill_effect": effect.strip(),
        })

    selected_families = [
        item.strip() for item in request.POST.getlist("family") if item.strip()
    ]

    raw_rank = request.POST.get("rank", "").strip()
    rank_val = raw_rank if raw_rank and raw_rank != "None" else RankChoices.N

    payload = {
        "name": request.POST.get("name", "").strip(),
        "attr": request.POST.get("attr", ""),
        "element": request.POST.get("element", ""),
        "stage": request.POST.get("stage", ""),
        "rank": rank_val,
        "family": selected_families,
        "role": request.POST.get("role", ""),
        "prior_evolutions": _split_csv(request.POST.get("prior_evolutions", "")),
        "next_evolutions": _split_csv(request.POST.get("next_evolutions", "")),
        "skills": skills,
    }

    if "image" in request.FILES:
        payload["image"] = request.FILES["image"]
    elif request.POST.get("clear_image") == "1":
        payload["image"] = None

    return payload


def _base_form_context(instance=None) -> dict:
    existing_skills = list(instance.skills.all()) if instance else []
    raw_family = instance.family if instance else []
    selected_families = _normalize_family_list(raw_family) if instance else []

    return {
        "is_update": instance is not None,
        "instance": instance,
        "form_action": (
            reverse("digimon-update", kwargs={"pk": instance.pk})
            if instance
            else reverse("digimon-create")
        ),
        "attr_choices": AttributeChoices.choices,
        "family_choices": FamilyChoices.choices,
        "rank_choices": RankChoices.choices,
        "role_choices": RoleChoices.choices,
        "element_choices": ElementChoices.choices,
        "stage_choices": StageChoices.choices,
        "selected_families": selected_families,
        "prior_evolutions_str": (
            ", ".join(instance.prior_evolutions)
            if instance and instance.prior_evolutions
            else ""
        ),
        "next_evolutions_str": (
            ", ".join(instance.next_evolutions)
            if instance and instance.next_evolutions
            else ""
        ),
        "existing_skills": existing_skills,
        "digimons": Digimon.objects.prefetch_related("skills").order_by("-id")[:10],
    }


@api_view(["GET"])
def get_digimon_by_name(request, name: str):
    clean_name = unquote(name).strip()
    digimon = get_object_or_404(
        Digimon.objects.prefetch_related("skills"),
        name__iexact=clean_name,
    )
    serializer = DigimonSerializer(digimon, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_digimon_by_id(request, pk: int):
    digimon = get_object_or_404(
        Digimon.objects.prefetch_related("skills"),
        pk=pk,
    )
    serializer = DigimonSerializer(digimon, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


def digimon_create_view(request):
    context = _base_form_context()

    if request.method == "POST":
        payload = _extract_digimon_payload(request)
        serializer = DigimonSerializer(data=payload, context={"request": request})
        if serializer.is_valid():
            digimon = serializer.save()
            context = _base_form_context()
            context["saved_digimon"] = digimon
            context["action_label"] = "kaydedildi"
            context["saved_json"] = _pretty_json(
                DigimonSerializer(digimon, context={"request": request}).data
            )
            return render(request, "digimon/partials/create_feedback.html", context)

        context["errors"] = serializer.errors
        return render(request, "digimon/partials/create_feedback.html", context, status=400)

    return render(request, "digimon/digimon_create.html", context)


def digimon_update_view(request, pk: int):
    digimon = get_object_or_404(Digimon.objects.prefetch_related("skills"), pk=pk)
    context = _base_form_context(instance=digimon)

    if request.method == "POST":
        payload = _extract_digimon_payload(request)
        serializer = DigimonSerializer(
            digimon, data=payload, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            updated_digimon = serializer.save()
            context = _base_form_context(instance=updated_digimon)
            context["saved_digimon"] = updated_digimon
            context["action_label"] = "güncellendi"
            context["saved_json"] = _pretty_json(
                DigimonSerializer(updated_digimon, context={"request": request}).data
            )
            return render(request, "digimon/partials/create_feedback.html", context)

        context["errors"] = serializer.errors
        return render(request, "digimon/partials/create_feedback.html", context, status=400)

    return render(request, "digimon/digimon_create.html", context)


def _pretty_json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def digimon_list_page(request):
    """Tüm kayıtlı Digimonları JSON formatında gösteren sayfa"""
    queryset = Digimon.objects.prefetch_related("skills").order_by("id")
    data = DigimonSerializer(queryset, many=True, context={"request": request}).data
    context = {
        "total_count": len(data),
        "json_output": _pretty_json(data),
        "endpoint_url": request.build_absolute_uri("/api/digimons/"),
    }
    return render(request, "digimon/digimon_list.html", context)


def digimon_by_name_page(request):
    """İsme göre Digimon sorgulayıp JSON formatında gösteren sayfa"""
    name = request.GET.get("name", "").strip()
    json_output = None
    error_message = None

    if name:
        digimon = Digimon.objects.prefetch_related("skills").filter(name__iexact=name).first()
        if digimon:
            data = DigimonSerializer(digimon, context={"request": request}).data
            json_output = _pretty_json(data)
        else:
            error_message = f'"{name}" adına sahip bir Digimon bulunamadı (HTTP 404).'

    endpoint_url = (
        request.build_absolute_uri(reverse("get-digimon-by-name", kwargs={"name": name}))
        if name
        else request.build_absolute_uri("/api/digimons/by-name/<name>/")
    )

    context = {
        "query_name": name,
        "json_output": json_output,
        "error_message": error_message,
        "endpoint_url": endpoint_url,
    }
    return render(request, "digimon/digimon_by_name.html", context)


def digimon_by_id_page(request):
    """ID'ye göre Digimon sorgulayıp JSON formatında gösteren sayfa"""
    raw_id = request.GET.get("id", "").strip()
    json_output = None
    error_message = None

    if raw_id:
        if raw_id.isdigit():
            pk = int(raw_id)
            digimon = Digimon.objects.prefetch_related("skills").filter(pk=pk).first()
            if digimon:
                data = DigimonSerializer(digimon, context={"request": request}).data
                json_output = _pretty_json(data)
            else:
                error_message = f"ID={pk} değerine sahip bir Digimon bulunamadı (HTTP 404)."
        else:
            error_message = "Lütfen geçerli bir sayısal ID girin."

    endpoint_url = (
        request.build_absolute_uri(reverse("get-digimon-by-id", kwargs={"pk": int(raw_id)}))
        if raw_id.isdigit()
        else request.build_absolute_uri("/api/digimons/by-id/<id>/")
    )

    context = {
        "query_id": raw_id,
        "json_output": json_output,
        "error_message": error_message,
        "endpoint_url": endpoint_url,
    }
    return render(request, "digimon/digimon_by_id.html", context)