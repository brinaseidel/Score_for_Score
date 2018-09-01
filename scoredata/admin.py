from django.contrib import admin

# Register your models here.
from .models import Gymnast, Country, Meet, Event, Score, Post, Author, Tag

admin.site.register(Gymnast)
admin.site.register(Country)
admin.site.register(Meet)
admin.site.register(Event)
admin.site.register(Score)

admin.site.register(Post)
admin.site.register(Author)
admin.site.register(Tag)
