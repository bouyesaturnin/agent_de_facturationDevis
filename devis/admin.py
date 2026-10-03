from django.contrib import admin
from .models import ArtisanProfile, Client, Chantier, MateriauPlomberie, Devis, LigneDevis

admin.site.register(ArtisanProfile)
admin.site.register(Client)
admin.site.register(Chantier)
admin.site.register(MateriauPlomberie)
admin.site.register(Devis)
admin.site.register(LigneDevis)
