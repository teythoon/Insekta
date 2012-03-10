from django.contrib import admin

from insekta.vm.models import BaseImage, VirtualMachine

admin.site.register(BaseImage)
admin.site.register(VirtualMachine)
