import ast
import json
from functools import reduce
from operator import or_
from urllib.parse import quote

from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from rest_framework import serializers
from .models import Digimon, FamilyChoices, Skill


def _normalize_family_list(raw):
    if isinstance(raw, list):
        if len(raw) > 5 and all(isinstance(item, str) and len(item) == 1 for item in raw):
            raw = "".join(raw)
        else:
            return [str(item).strip() for item in raw if str(item).strip()]

    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            for parser in (json.loads, ast.literal_eval):
                try:
                    parsed = parser(text)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
        return [item.strip() for item in text.split(",") if item.strip()]

    return []


def _normalize_evolution_names(raw):
    if not isinstance(raw, list):
        return []
    cleaned = []
    for item in raw:
        if isinstance(item, dict):
            name = str(item.get("name", "")).strip()
        else:
            name = str(item).strip()
        if name:
            cleaned.append(name)
    return cleaned


def build_digimon_url(target, request=None):
    by_name_path = reverse("get-digimon-by-name", kwargs={"name": quote(target.name)})
    if request:
        return request.build_absolute_uri(by_name_path)
    return by_name_path


class SkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(max_length=100, validators=[])
    skill_effect = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default="",
    )

    class Meta:
        model = Skill
        fields = ["skill_name", "skill_attr", "skill_damage", "skill_effect"]

    def validate_skill_effect(self, value):
        return (value or "").strip()


class DigimonSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True)
    family = serializers.ListField(
        child=serializers.ChoiceField(choices=FamilyChoices.choices),
        required=False,
        default=list,
    )
    prior_evolutions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    next_evolutions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )

    class Meta:
        model = Digimon
        fields = [
            "id",
            "name",
            "attr",
            "element",
            "stage",
            "rank",
            "family",
            "role",
            "prior_evolutions",
            "next_evolutions",
            "skills",
            "image",
        ]

    def _get_digimon_lookup(self, cleaned_names):
        cache = self.context.setdefault("_digimon_lookup_cache", {})
        missing = [n for n in cleaned_names if n.lower() not in cache]

        if missing:
            query = reduce(or_, (Q(name__iexact=n) for n in missing))
            found = {d.name.lower(): d for d in Digimon.objects.filter(query)}
            for n in missing:
                cache[n.lower()] = found.get(n.lower())

        return cache

    def _format_evolutions(self, names, request=None):
        cleaned_names = _normalize_evolution_names(names)
        if not cleaned_names:
            return []

        matched = self._get_digimon_lookup(cleaned_names)

        resolved = []
        for raw_name in cleaned_names:
            target = matched.get(raw_name.lower())
            if target:
                resolved.append({
                    "name": target.name,
                    "exists": True,
                    "url": build_digimon_url(target, request=request),
                })
            else:
                resolved.append({
                    "name": raw_name,
                    "exists": False,
                    "url": None,
                })

        return resolved

    def validate_rank(self, value):
        if not value or str(value).strip() in ("", "None", "none"):
            return "N"
        return str(value).strip()

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get("request")

        if not rep.get("rank") or rep.get("rank") == "None":
            rep["rank"] = "N"

        fam = rep.get("family")
        if isinstance(fam, list) and len(fam) > 3 and all(isinstance(x, str) and len(x) == 1 for x in fam):
            joined = "".join(fam)
            for parser in (json.loads, ast.literal_eval):
                try:
                    parsed = parser(joined)
                    if isinstance(parsed, list):
                        rep["family"] = [str(x).strip() for x in parsed if str(x).strip()]
                        break
                except Exception:
                    pass

        rep["prior_evolutions"] = self._format_evolutions(
            instance.prior_evolutions, request=request
        )
        rep["next_evolutions"] = self._format_evolutions(
            instance.next_evolutions, request=request
        )

        return rep

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            mutable_data = data.copy()
        else:
            mutable_data = dict(data)

        raw_rank = mutable_data.get("rank")
        if raw_rank is None or str(raw_rank).strip() in ("", "None", "none"):
            mutable_data["rank"] = "N"

        if "family" in mutable_data:
            if hasattr(mutable_data, "getlist"):
                vals = mutable_data.getlist("family")
                if len(vals) == 1:
                    normalized = _normalize_family_list(vals[0])
                else:
                    normalized = _normalize_family_list(vals)
                mutable_data.setlist("family", normalized)
            else:
                mutable_data["family"] = _normalize_family_list(mutable_data["family"])

        for evo_field in ("prior_evolutions", "next_evolutions"):
            if evo_field in mutable_data and not hasattr(mutable_data, "getlist"):
                mutable_data[evo_field] = _normalize_evolution_names(mutable_data[evo_field])

        return super().to_internal_value(mutable_data)

    def validate_skills(self, value):
        if not (1 <= len(value) <= 4):
            raise serializers.ValidationError(
                "Her Digimon en az 1, en fazla 4 adet skill sahibi olabilir."
            )

        seen_names = set()
        for item in value:
            s_name = item.get("skill_name", "").strip().lower()
            if s_name in seen_names:
                raise serializers.ValidationError(
                    f"Aynı Digimon için '{item.get('skill_name')}' skilli birden fazla kez eklenemez."
                )
            seen_names.add(s_name)

        return value

    @transaction.atomic
    def create(self, validated_data):
        skills_data = validated_data.pop("skills", [])
        digimon = Digimon.objects.create(**validated_data)
        for skill_data in skills_data:
            skill_data["skill_effect"] = (skill_data.get("skill_effect") or "").strip()
            Skill.objects.create(digimon=digimon, **skill_data)
        return digimon

    @transaction.atomic
    def update(self, instance, validated_data):
        skills_data = validated_data.pop("skills", None)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        if skills_data is not None:
            instance.skills.all().delete()
            for skill_data in skills_data:
                skill_data["skill_effect"] = (skill_data.get("skill_effect") or "").strip()
                Skill.objects.create(digimon=instance, **skill_data)

        return instance