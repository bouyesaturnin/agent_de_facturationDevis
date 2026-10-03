from django.db import models
from django.conf import settings
from decimal import Decimal

METIER_CHOICES = [
    ('plomberie',   'Plomberie & Sanitaire'),
    ('menuiserie',  'Menuiserie & Bois'),
    ('electricite', 'Électricité'),
    ('maconnerie',  'Maçonnerie & Gros œuvre'),
    ('peinture',    'Peinture & Revêtements'),
    ('carrelage',   'Carrelage & Sols'),
    ('chauffage',   'Chauffage & Climatisation'),
    ('autre',       'Autre / Multi-métiers'),
]


class ArtisanProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profil')
    nom_entreprise = models.CharField(max_length=200)
    siret = models.CharField(max_length=14)
    tva_intracommunautaire = models.CharField(max_length=20, blank=True)
    adresse = models.TextField()
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    assurance_nom = models.CharField(max_length=200)
    assurance_police_numero = models.CharField(max_length=100)
    assurance_zone_couverture = models.CharField(max_length=200, blank=True)
    validite_devis_jours = models.PositiveIntegerField(default=30)
    mentions_paiement = models.TextField(blank=True, default='')
    metier = models.CharField(max_length=20, choices=METIER_CHOICES, default='plomberie')

    def __str__(self):
        return self.nom_entreprise


class Client(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='clients')
    nom = models.CharField(max_length=200)
    adresse = models.TextField()
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.nom


class Chantier(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="chantiers")
    adresse = models.TextField()
    date_creation = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Chantier {self.adresse[:40]} ({self.client.nom})"


class MateriauPlomberie(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='materiaux')
    nom = models.CharField(max_length=200)
    reference = models.CharField(max_length=100, blank=True)
    categorie = models.CharField(max_length=30, default="autre")
    metier = models.CharField(max_length=20, choices=METIER_CHOICES, default='plomberie')
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    unite = models.CharField(max_length=20, default="pièce")

    def __str__(self):
        return f"{self.nom} ({self.prix_unitaire} €/{self.unite})"


class Devis(models.Model):
    STATUT_CHOICES = [
        ("brouillon", "Brouillon"),
        ("envoye", "Envoyé"),
        ("accepte", "Accepté"),
        ("refuse", "Refusé"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='devis')
    numero = models.CharField(max_length=50)
    date_creation = models.DateField(auto_now_add=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="devis")
    chantier = models.ForeignKey(Chantier, on_delete=models.SET_NULL, null=True, blank=True, related_name="devis")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="brouillon")
    objet = models.TextField(blank=True, default='')
    metier = models.CharField(max_length=20, choices=METIER_CHOICES, default='plomberie')

    class Meta:
        unique_together = ('user', 'numero')

    def __str__(self):
        return f"Devis {self.numero} - {self.client.nom}"

    @property
    def total_ht(self):
        return sum(ligne.total_ligne for ligne in self.lignes.all())


class LigneDevis(models.Model):
    TVA_CHOICES = [
        (Decimal("20"), "20%"),
        (Decimal("10"), "10%"),
        (Decimal("5.5"), "5.5%"),
    ]
    devis = models.ForeignKey(Devis, on_delete=models.CASCADE, related_name="lignes")
    materiau = models.ForeignKey(MateriauPlomberie, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=300)
    quantite = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    tva = models.DecimalField(max_digits=4, decimal_places=1, choices=TVA_CHOICES, default=Decimal("20"))

    @property
    def total_ligne(self):
        return self.quantite * self.prix_unitaire

    def __str__(self):
        return f"{self.description} x{self.quantite}"
