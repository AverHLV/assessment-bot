from django.contrib import admin


class DictionaryAdmin(admin.ModelAdmin):
    list_display = 'id', 'code', 'name'
    list_display_links = list_display
