from django.db import models

from ripplesite.ripple.models import Node

class Advertisement(models.Model):
    user = models.ForeignKey(Node)
    title = models.CharField(max_length=255)
    text = models.TextField()
    posted_date = models.DateTimeField(auto_now_add=True)

    class Admin:
        list_display = ('user', 'title', 'posted_date')
        search_fields = ('user', 'title', 'text')

    def __str__(self):
        return self.title

