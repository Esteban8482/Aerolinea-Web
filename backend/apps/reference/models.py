from django.db import models


class Country(models.Model):
    id = models.PositiveIntegerField(primary_key=True)  # Pinned source IDs, never name-based IDs.
    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=160)
    search_text = models.TextField()
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "pk"]


class Subdivision(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="subdivisions")
    code = models.CharField(max_length=30, blank=True)
    name = models.CharField(max_length=200)
    search_text = models.TextField()
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "pk"]


class Locality(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="localities")
    subdivision = models.ForeignKey(
        Subdivision, null=True, on_delete=models.PROTECT, related_name="localities"
    )
    name = models.CharField(max_length=200)
    search_text = models.TextField()
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "pk"]
        indexes = [models.Index(fields=["country", "subdivision", "active"])]

    @property
    def label(self):
        return ", ".join(
            x
            for x in [
                self.name,
                self.subdivision.name if self.subdivision else "",
                self.country.name,
            ]
            if x
        )


class Option(models.Model):
    category = models.CharField(max_length=40)
    code = models.CharField(max_length=30)
    label = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["category", "position", "code"]
        constraints = [
            models.UniqueConstraint(fields=["category", "code"], name="reference_option_code")
        ]
