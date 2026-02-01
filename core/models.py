from django.db import models


class Directory(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)

    class Meta:
        abstract = True

    def __str__(self):
        return f'{type(self).__name__} {self.id}: {self.name}'


class TimeStamped(models.Model):
    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
