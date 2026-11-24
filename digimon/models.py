from django.db import models


class AttributeChoices(models.TextChoices):
    VACCINE = "Vaccine", "Vaccine"
    DATA = "Data", "Data"
    VIRUS = "Virus", "Virus"
    UNKNOWN = "Unknown", "Unknown"
    NONE = "None", "None"


class RankChoices(models.TextChoices):
    N = "N", "N"
    A = "A", "A"
    A_PLUS = "A+", "A+"
    S = "S", "S"
    SS = "SS", "SS"
    SS_PLUS = "SS+", "SS+"
    SSS = "SSS", "SSS"
    SSS_PLUS = "SSS+", "SSS+"
    U = "U", "U"


class StageChoices(models.TextChoices):
    ROOKIE = "Rookie", "Rookie"
    ROOKIE_X = "Rookie X", "Rookie X"
    CHAMPION = "Champion", "Champion"
    CHAMPION_X = "Champion X", "Champion X"
    ULTIMATE = "Ultimate", "Ultimate"
    ULTIMATE_X = "Ultimate X", "Ultimate X"
    MEGA = "Mega", "Mega"
    MEGA_X = "Mega X", "Mega X"
    SIDE_MEGA = "Side Mega", "Side Mega"
    BURST_MODE = "Burst Mode", "Burst Mode"
    BURST_MODE_X = "Burst Mode X", "Burst Mode X"
    JOGRESS = "Jogress", "Jogress"
    JOGRESS_X = "Jogress X", "Jogress X"
    ARMOR = "Armor", "Armor"
    VARIANT = "Variant", "Variant"
    HYBRID = "Hybrid", "Hybrid"


class RoleChoices(models.TextChoices):
    MELEE_DPS = "Melee DPS", "Melee DPS"
    RANGED_DPS = "Ranged DPS", "Ranged DPS"
    CASTER = "Caster", "Caster"
    TANK = "Tank", "Tank"
    HEALER = "Healer", "Healer"
    SUPPORT = "Support", "Support"


class ElementChoices(models.TextChoices):
    FIRE = "Fire", "Fire"
    ICE = "Ice", "Ice"
    EARTH = "Earth", "Earth"
    LIGHT = "Light", "Light"
    STEEL = "Steel", "Steel"
    DARKNESS = "Darkness", "Darkness"
    THUNDER = "Thunder", "Thunder"
    WATER = "Water", "Water"
    WOOD = "Wood", "Wood"
    WIND = "Wind", "Wind"


class FamilyChoices(models.TextChoices):
    DARK_AREA = "Dark Area", "Dark Area"
    DEEP_SAVERS = "Deep Savers", "Deep Savers"
    DRAGONS_ROARS = "Dragon's Roars", "Dragon's Roars"
    JUNGLE_TROOPERS = "Jungle Troopers", "Jungle Troopers"
    METAL_EMPIRE = "Metal Empire", "Metal Empire"
    NATURE_SPIRITS = "Nature Spirits", "Nature Spirits"
    NIGHTMARE_SOLDIERS = "Nightmare Soldiers", "Nightmare Soldiers"
    UNKNOWN = "Unknown", "Unknown"
    VIRUS_BUSTERS = "Virus Busters", "Virus Busters"
    WIND_GUARDIANS = "Wind Guardians", "Wind Guardians"


class Digimon(models.Model):
    name = models.CharField(max_length=100, unique=True)
    attr = models.CharField(
        max_length=100,
        choices=AttributeChoices.choices,
        default=AttributeChoices.NONE,
    )
    element = models.CharField(max_length=100, choices=ElementChoices.choices)
    stage = models.CharField(max_length=100, choices=StageChoices.choices)
    rank = models.CharField(
        max_length=100,
        choices=RankChoices.choices,
        default=RankChoices.N,
        blank=True,
    )
    family = models.JSONField(default=list, blank=True)
    role = models.CharField(max_length=100, choices=RoleChoices.choices)
    prior_evolutions = models.JSONField(default=list, blank=True)
    next_evolutions = models.JSONField(default=list, blank=True)
    # Not: settings.py'de MEDIA_ROOT zaten "media/" klasörüyse upload_to="digimons/" kullanman daha temiz olur.
    image = models.ImageField(upload_to="media/digimons/", blank=True, null=True)

    def __str__(self):
        return self.name


class Skill(models.Model):
    digimon = models.ForeignKey(
        Digimon,
        on_delete=models.CASCADE,
        related_name="skills",
    )
    skill_name = models.CharField(max_length=100)
    skill_attr = models.CharField(max_length=20, choices=ElementChoices.choices)
    skill_damage = models.PositiveSmallIntegerField()
    skill_effect = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["digimon", "skill_name"],
                name="unique_skill_per_digimon",
            )
        ]

    def __str__(self):
        return f"{self.digimon.name} - {self.skill_name}"