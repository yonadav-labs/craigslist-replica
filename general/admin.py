# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import *

class CategoryAdmin(admin.ModelAdmin):
	list_display = ['name', 'parent', 'columns', 'column']
	search_fields = ['name']

admin.site.register(UserProfile)
# admin.site.register(Contact)
admin.site.register(Post)
admin.site.register(Favourite)
admin.site.register(Hidden)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Search)
admin.site.register(Country)
admin.site.register(State)
admin.site.register(City)
