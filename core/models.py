from django.db import models

class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    is_completed = models.BooleanField(default=False)  # end status

    def __str__(self):
        return self.name

class Place(models.Model):
    project = models.ForeignKey(Project, related_name='places', on_delete=models.CASCADE)
    artwork_id = models.IntegerField()  
    title = models.CharField(max_length=255, blank=True) 
    image_id = models.CharField(max_length=255, blank=True, null=True) 
    notes = models.TextField(blank=True, default='')
    visited = models.BooleanField(default=False)

    class Meta:
        unique_together = ('project', 'artwork_id')

    def __str__(self):
        return f"{self.artwork_id} in {self.project.name}"
    