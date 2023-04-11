from datetime import datetime

from django.db import models

from base.models import CreatedModifiedTimeStampModel
from users.models import User
from snapshots.linkedin.models import (
    TargetAudienceSnapshot,
)


class Order(CreatedModifiedTimeStampModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)

    # NOTE: consider changing currency to choices
    currency = models.CharField(default="credits", max_length=200)
    total_charge = models.PositiveIntegerField(default=0)
    service_charge = models.PositiveIntegerField(default=0)
    tas = models.ForeignKey(TargetAudienceSnapshot, on_delete=models.SET_NULL, blank=True, null=True)
