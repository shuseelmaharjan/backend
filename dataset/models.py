from django.db import models
from django.core.exceptions import ValidationError

def validate_csv_file(value):
    if not value.name.endswith('.csv'):
        raise ValidationError("Only .csv files are allowed.")

class Dataset(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='datasets/', validators=[validate_csv_file])

    def __str__(self):
        return self.name
