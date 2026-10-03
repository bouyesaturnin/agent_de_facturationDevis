from rest_framework import serializers
from .models import Client, Chantier, MateriauPlomberie, Devis, LigneDevis
from .models import ArtisanProfile

class ArtisanProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtisanProfile
        fields = "__all__"
        read_only_fields = ('user',)


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"
        read_only_fields = ('user',)


class ChantierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chantier
        fields = "__all__"


class MateriauPlomberieSerializer(serializers.ModelSerializer):
    class Meta:
        model = MateriauPlomberie
        fields = "__all__"
        read_only_fields = ('user',)


class LigneDevisSerializer(serializers.ModelSerializer):
    total_ligne = serializers.ReadOnlyField()

    class Meta:
        model = LigneDevis
        fields = "__all__"


class DevisSerializer(serializers.ModelSerializer):
    lignes = LigneDevisSerializer(many=True, read_only=True)
    total_ht = serializers.ReadOnlyField()
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    client_adresse = serializers.CharField(source='client.adresse', read_only=True)
    client_email = serializers.CharField(source='client.email', read_only=True, default='')
    chantier_adresse = serializers.CharField(source='chantier.adresse', read_only=True, default='')

    class Meta:
        model = Devis
        fields = "__all__"
        read_only_fields = ('user',)