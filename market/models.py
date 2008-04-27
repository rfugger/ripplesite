from django.db import models

from ripplesite.ripple.models import Node

class Advertisement(models.Model):
    user = models.ForeignKey(Node)
    title = models.CharField(max_length=255)
    text = models.TextField()
    location = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    posted_date = models.DateTimeField(auto_now_add=True)

    class Admin:
        list_display = ('user', 'title', 'location', 'category', 'posted_date')
        search_fields = ('user', 'title', 'location', 'category', 'text')

    def __str__(self):
        return self.title

