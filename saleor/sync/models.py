from django.db import models


class QueueJob(models.Model):
    command_type = models.CharField(max_length=250)
    output = models.TextField(blank=True, null=True)
    status = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=None, editable=False, null=True)
    started_at = models.DateTimeField(default=None, editable=False, null=True)
    completed_at = models.DateTimeField(default=None, editable=False, null=True)
