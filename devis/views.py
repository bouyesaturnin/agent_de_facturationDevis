from io import BytesIO
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import viewsets, status
from django.core.mail import EmailMultiAlternatives
from django.conf import settings as django_settings
from django.contrib.auth.models import User
from .models import Client, Chantier, MateriauPlomberie, Devis, LigneDevis, ArtisanProfile
from .serializers import (
    ClientSerializer, ChantierSerializer, MateriauPlomberieSerializer,
    DevisSerializer, LigneDevisSerializer, ArtisanProfileSerializer,
)


# ── PDF helpers ────────────────────────────────────────────────────────────────

def _calcul_totaux(devis):
    from decimal import Decimal
    total_ht = Decimal('0')
    total_tva = Decimal('0')
    lignes = []
    for ligne in devis.lignes.all():
        ht = ligne.quantite * ligne.prix_unitaire
        tva = ht * (ligne.tva / 100)
        total_ht += ht
        total_tva += tva
        lignes.append({'ligne': ligne, 'ht': ht})
    return total_ht, total_tva, total_ht + total_tva, lignes


def _build_email_html(devis, artisan, message_perso=''):
    total_ht, total_tva, total_ttc, lignes_data = _calcul_totaux(devis)

    lignes_html = ''
    for item in lignes_data:
        l = item['ligne']
        lignes_html += f"""<tr>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;">{l.description}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">{l.quantite}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:right;">{l.prix_unitaire:.2f} €</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">{l.tva}%</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:right;">{item['ht']:.2f} €</td>
        </tr>"""

    artisan_bloc = ''
    if artisan:
        tel = f"<p style='margin:2px 0 0;color:#64748b;font-size:13px;'>Tél : {artisan.telephone}</p>" if artisan.telephone else ''
        ass = f"<p style='margin:2px 0 0;color:#64748b;font-size:13px;'>Assurance : {artisan.assurance_nom} — Police n° {artisan.assurance_police_numero}</p>" if artisan.assurance_nom else ''
        artisan_bloc = f"""
        <p style="margin:0;font-size:18px;font-weight:700;color:#1e293b;">{artisan.nom_entreprise}</p>
        <p style="margin:4px 0 0;color:#64748b;font-size:13px;">{artisan.adresse}</p>
        <p style="margin:2px 0 0;color:#64748b;font-size:13px;">SIRET : {artisan.siret}</p>
        {tel}{ass}"""

    texte_intro = message_perso or (devis.objet or '')
    message_bloc = f"""<div style="margin:24px 0;padding:16px;background:#f0f9ff;border-left:4px solid #0ea5e9;border-radius:4px;">
      <p style="margin:0;color:#0369a1;font-size:14px;white-space:pre-wrap;">{texte_intro}</p>
    </div>""" if texte_intro else ''

    chantier_ligne = f"<p style='margin:2px 0 0;color:#64748b;font-size:13px;'>Chantier : {devis.chantier.adresse}</p>" if devis.chantier else ''
    validite = f"<p style='margin:8px 0 0;color:#64748b;font-size:12px;'>Ce devis est valable {artisan.validite_devis_jours} jours.</p>" if artisan and artisan.validite_devis_jours else ''
    mentions = f"<p style='margin:8px 0 0;color:#64748b;font-size:12px;'>{artisan.mentions_paiement}</p>" if artisan and artisan.mentions_paiement else ''

    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:Arial,sans-serif;">
  <div style="max-width:700px;margin:32px auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08);">
    <div style="background:#1e293b;padding:28px 32px;">
      <table style="width:100%;border-collapse:collapse;"><tr>
        <td style="vertical-align:top;">{artisan_bloc}</td>
        <td style="text-align:right;vertical-align:top;">
          <p style="margin:0;font-size:28px;font-weight:800;color:#fff;letter-spacing:2px;">DEVIS</p>
          <p style="margin:4px 0 0;color:#94a3b8;font-size:14px;">{devis.numero}</p>
          <p style="margin:2px 0 0;color:#94a3b8;font-size:13px;">{devis.date_creation.strftime('%d/%m/%Y')}</p>
        </td>
      </tr></table>
    </div>
    <div style="padding:28px 32px;">
      {message_bloc}
      <div style="margin-bottom:24px;padding:16px;background:#f8fafc;border-radius:6px;">
        <p style="margin:0;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#94a3b8;">Destinataire</p>
        <p style="margin:6px 0 0;font-size:16px;font-weight:700;color:#1e293b;">{devis.client.nom}</p>
        <p style="margin:2px 0 0;color:#64748b;font-size:13px;">{devis.client.adresse}</p>
        {chantier_ligne}
      </div>
      <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
        <thead><tr style="background:#f1f5f9;">
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#64748b;">Désignation</th>
          <th style="padding:10px 12px;text-align:center;font-size:12px;color:#64748b;">Qté</th>
          <th style="padding:10px 12px;text-align:right;font-size:12px;color:#64748b;">P.U. HT</th>
          <th style="padding:10px 12px;text-align:center;font-size:12px;color:#64748b;">TVA</th>
          <th style="padding:10px 12px;text-align:right;font-size:12px;color:#64748b;">Total HT</th>
        </tr></thead>
        <tbody>{lignes_html}</tbody>
      </table>
      <table style="margin-left:auto;width:260px;border-collapse:collapse;border-top:2px solid #e2e8f0;">
        <tr><td style="padding:6px 0;font-size:14px;color:#475569;">Total HT</td><td style="text-align:right;font-size:14px;color:#475569;">{total_ht:.2f} €</td></tr>
        <tr><td style="padding:6px 0;font-size:14px;color:#475569;">TVA</td><td style="text-align:right;font-size:14px;color:#475569;">{total_tva:.2f} €</td></tr>
        <tr style="border-top:2px solid #1e293b;"><td style="padding:10px 0;font-size:16px;font-weight:700;color:#1e293b;">Total TTC</td><td style="text-align:right;font-size:16px;font-weight:700;color:#1e293b;">{total_ttc:.2f} €</td></tr>
      </table>
      <div style="margin-top:32px;padding-top:20px;border-top:1px solid #e2e8f0;">
        {validite}{mentions}
        <p style="margin:12px 0 0;color:#94a3b8;font-size:11px;">Pour accepter ce devis, retournez ce document signé avec la mention "Bon pour accord".</p>
      </div>
    </div>
  </div>
</body></html>"""


def _build_pdf_html(devis, artisan):
    total_ht, total_tva, total_ttc, lignes_data = _calcul_totaux(devis)

    lignes_rows = ''
    for i, item in enumerate(lignes_data):
        l = item['ligne']
        bg = 'background:#EFF6FF;' if i % 2 == 0 else ''
        lignes_rows += f"""<tr style="{bg}">
          <td style="padding:7px 8px;border-bottom:1px solid #EDE8DE;font-size:11px;color:#2C3442;">{l.description}</td>
          <td style="padding:7px 8px;border-bottom:1px solid #EDE8DE;font-size:11px;color:#2C3442;text-align:right;">{l.quantite}</td>
          <td style="padding:7px 8px;border-bottom:1px solid #EDE8DE;font-size:11px;color:#2C3442;text-align:right;">{l.prix_unitaire:.2f} &#8364;</td>
          <td style="padding:7px 8px;border-bottom:1px solid #EDE8DE;font-size:11px;color:#2C3442;text-align:center;">{l.tva}%</td>
          <td style="padding:7px 8px;border-bottom:1px solid #EDE8DE;font-size:11px;color:#2C3442;text-align:right;">{item['ht']:.2f} &#8364;</td>
        </tr>"""

    tva_intra = f" &mdash; TVA intra : {artisan.tva_intracommunautaire}" if artisan and artisan.tva_intracommunautaire else ''
    email_art = f" &mdash; {artisan.email}" if artisan and artisan.email else ''
    assurance_row = ''
    if artisan and artisan.assurance_nom:
        zone = f" ({artisan.assurance_zone_couverture})" if artisan.assurance_zone_couverture else ''
        assurance_row = f"<p style='font-size:11px;color:#5A6475;line-height:1.6;font-style:italic;margin:2px 0;'>Assurance d&eacute;cennale&nbsp;: {artisan.assurance_nom}, police n&deg; {artisan.assurance_police_numero}{zone}</p>"

    chantier_row = f"<p style='font-size:11px;color:#7A8494;font-style:italic;margin:2px 0;'>Chantier&nbsp;: {devis.chantier.adresse}</p>" if devis.chantier else ''
    objet_bloc = f"""<div style="margin-bottom:18px;padding:10px 14px;background:#EFF6FF;border-left:3px solid #2563EB;border-radius:0 4px 4px 0;">
      <p style="margin:0;font-size:12px;color:#1D4ED8;line-height:1.6;">{devis.objet}</p>
    </div>""" if devis.objet else ''

    validite_jours = artisan.validite_devis_jours if artisan else 30
    mentions = f"<p style='margin:2px 0;'>{artisan.mentions_paiement}</p>" if artisan and artisan.mentions_paiement else ''
    date_fr = devis.date_creation.strftime('%d/%m/%Y')
    nom_artisan = artisan.nom_entreprise if artisan else 'Artisan'
    adresse_art = artisan.adresse if artisan else ''
    siret_art = artisan.siret if artisan else ''
    tel_art = artisan.telephone if artisan else ''

    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
<style>
  @page {{ margin: 2cm 2.5cm; }}
  body {{ font-family: Helvetica, Arial, sans-serif; font-size: 12px; color: #1E252F; margin: 0; padding: 0; }}
</style>
</head><body>
  <table style="width:100%;border-collapse:collapse;margin-bottom:20px;"><tr>
    <td style="vertical-align:top;padding:0;">
      <p style="margin:0 0 4px;font-size:17px;font-weight:bold;color:#1E252F;">{nom_artisan}</p>
      <p style="margin:2px 0;font-size:11px;color:#5A6475;line-height:1.6;">{adresse_art}</p>
      <p style="margin:2px 0;font-size:11px;color:#5A6475;line-height:1.6;">SIRET&nbsp;: {siret_art}{tva_intra}</p>
      <p style="margin:2px 0;font-size:11px;color:#5A6475;line-height:1.6;">T&eacute;l&nbsp;: {tel_art}{email_art}</p>
      {assurance_row}
    </td>
    <td style="text-align:right;vertical-align:top;padding:0;">
      <p style="margin:0;font-size:34px;font-weight:bold;color:#1E252F;letter-spacing:3px;">DEVIS</p>
      <p style="margin:4px 0 0;font-size:12px;color:#1E252F;font-family:Courier,monospace;">{devis.numero}</p>
      <p style="margin:2px 0 0;font-size:11px;color:#5A6475;">{date_fr}</p>
    </td>
  </tr></table>
  <hr style="border:0;border-top:2px solid #2563EB;margin:0 0 20px;"/>
  {objet_bloc}
  <div style="margin-bottom:20px;padding:12px 14px;background:#EFF6FF;border-radius:4px;">
    <p style="margin:0 0 5px;font-size:9px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;color:#94A3B8;">Destinataire</p>
    <p style="margin:0 0 2px;font-size:14px;font-weight:bold;color:#1E252F;">{devis.client.nom}</p>
    <p style="margin:0;font-size:12px;color:#5A6475;">{devis.client.adresse}</p>
    {chantier_row}
  </div>
  <table style="width:100%;border-collapse:collapse;margin-bottom:18px;">
    <thead><tr style="border-bottom:2px solid #1E252F;">
      <th style="padding:7px 8px;text-align:left;font-size:9px;font-weight:bold;text-transform:uppercase;color:#5A6475;">D&eacute;signation</th>
      <th style="padding:7px 8px;text-align:right;font-size:9px;font-weight:bold;text-transform:uppercase;color:#5A6475;">Qt&eacute;</th>
      <th style="padding:7px 8px;text-align:right;font-size:9px;font-weight:bold;text-transform:uppercase;color:#5A6475;">P.U. HT</th>
      <th style="padding:7px 8px;text-align:center;font-size:9px;font-weight:bold;text-transform:uppercase;color:#5A6475;">TVA</th>
      <th style="padding:7px 8px;text-align:right;font-size:9px;font-weight:bold;text-transform:uppercase;color:#5A6475;">Total HT</th>
    </tr></thead>
    <tbody>{lignes_rows}</tbody>
  </table>
  <table style="width:220px;border-collapse:collapse;margin-left:auto;margin-bottom:24px;">
    <tr><td style="padding:4px 0;font-size:12px;color:#5A6475;">Total HT</td><td style="padding:4px 0;font-size:12px;color:#2C3442;text-align:right;font-family:Courier,monospace;">{total_ht:.2f} &#8364;</td></tr>
    <tr><td style="padding:4px 0;font-size:12px;color:#5A6475;">Total TVA</td><td style="padding:4px 0;font-size:12px;color:#2C3442;text-align:right;font-family:Courier,monospace;">{total_tva:.2f} &#8364;</td></tr>
    <tr style="border-top:2px solid #1E252F;">
      <td style="padding:8px 0 4px;font-size:15px;font-weight:bold;color:#1E252F;">Total TTC</td>
      <td style="padding:8px 0 4px;font-size:17px;font-weight:bold;color:#2563EB;text-align:right;font-family:Courier,monospace;">{total_ttc:.2f} &#8364;</td>
    </tr>
  </table>
  <div style="margin-top:20px;padding-top:10px;border-top:1px solid #E5E0D6;">
    <p style="margin:2px 0;font-size:10px;color:#8A94A0;font-style:italic;">Devis valable {validite_jours} jours &agrave; compter de sa date d&apos;&eacute;mission.</p>
    {mentions}
    <p style="margin:2px 0;font-size:10px;color:#8A94A0;font-style:italic;">Pour accord, veuillez retourner ce document sign&eacute; avec la mention &laquo;&nbsp;Bon pour accord&nbsp;&raquo;.</p>
  </div>
</body></html>"""


def _generate_pdf(html_content):
    try:
        from xhtml2pdf import pisa
        buf = BytesIO()
        pisa.CreatePDF(html_content, dest=buf, encoding='utf-8')
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        return None


# ── Auth views ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def ping(request):
    return Response({"status": "ok", "message": "DevisFlash backend connecté"})


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()
    email    = request.data.get('email', '').strip()

    if not username or not password:
        return Response({'erreur': 'Nom d\'utilisateur et mot de passe requis.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(password) < 6:
        return Response({'erreur': 'Le mot de passe doit contenir au moins 6 caractères.'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({'erreur': 'Ce nom d\'utilisateur est déjà pris.'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, password=password, email=email)
    return Response({'message': f'Compte créé pour {username}. Vous pouvez maintenant vous connecter.'}, status=status.HTTP_201_CREATED)


# ── Devis helpers ──────────────────────────────────────────────────────────────

@api_view(['GET'])
def generate_numero(request):
    from datetime import date
    year = date.today().year
    prefix = f'DEV-{year}-'
    numeros = Devis.objects.filter(user=request.user, numero__startswith=prefix).values_list('numero', flat=True)
    max_seq = 0
    for num in numeros:
        try:
            seq = int(num[len(prefix):])
            if seq > max_seq:
                max_seq = seq
        except ValueError:
            pass
    return Response({'numero': f'{prefix}{max_seq + 1:03d}'})


# ── ViewSets (filtrés par utilisateur) ────────────────────────────────────────

class ArtisanProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ArtisanProfileSerializer
    queryset = ArtisanProfile.objects.none()

    def get_queryset(self):
        return ArtisanProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    queryset = Client.objects.none()

    def get_queryset(self):
        return Client.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ChantierViewSet(viewsets.ModelViewSet):
    serializer_class = ChantierSerializer
    queryset = Chantier.objects.none()

    def get_queryset(self):
        return Chantier.objects.filter(client__user=self.request.user)


class MateriauPlomberieViewSet(viewsets.ModelViewSet):
    serializer_class = MateriauPlomberieSerializer
    queryset = MateriauPlomberie.objects.none()

    def get_queryset(self):
        qs = MateriauPlomberie.objects.filter(user=self.request.user)
        metier = self.request.query_params.get('metier')
        if metier:
            qs = qs.filter(metier=metier)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DevisViewSet(viewsets.ModelViewSet):
    serializer_class = DevisSerializer
    queryset = Devis.objects.none()

    def get_queryset(self):
        return Devis.objects.filter(user=self.request.user).select_related('client', 'chantier').prefetch_related('lignes')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='envoyer-email')
    def envoyer_email(self, request, pk=None):
        devis = self.get_object()
        client = devis.client

        if not client.email:
            return Response(
                {'erreur': f"Le client « {client.nom} » n'a pas d'adresse email. Ajoutez-en une dans sa fiche."},
                status=status.HTTP_400_BAD_REQUEST
            )

        artisan = ArtisanProfile.objects.filter(user=request.user).first()
        message_perso = request.data.get('message_perso', '').strip()
        nom_artisan = artisan.nom_entreprise if artisan else 'Votre artisan'

        corps_texte = f"Bonjour {client.nom},\n\nVeuillez trouver votre devis {devis.numero} en pièce jointe PDF.\n"
        if message_perso:
            corps_texte += f"\n{message_perso}\n"
        corps_texte += f"\nCordialement,\n{nom_artisan}"

        html_email = _build_email_html(devis, artisan, message_perso)
        pdf_bytes  = _generate_pdf(_build_pdf_html(devis, artisan))

        try:
            msg = EmailMultiAlternatives(
                subject=f"Devis {devis.numero} — {nom_artisan}",
                body=corps_texte,
                from_email=django_settings.DEFAULT_FROM_EMAIL or 'noreply@devisflash.fr',
                to=[client.email],
            )
            msg.attach_alternative(html_email, "text/html")
            if pdf_bytes:
                msg.attach(f"{devis.numero}.pdf", pdf_bytes, 'application/pdf')
            msg.send(fail_silently=False)
        except Exception as e:
            return Response({'erreur': f"Échec d'envoi : {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if devis.statut == 'brouillon':
            devis.statut = 'envoye'
            devis.save(update_fields=['statut'])

        return Response({'message': f"Devis envoyé à {client.email}", 'statut': devis.statut})


class LigneDevisViewSet(viewsets.ModelViewSet):
    serializer_class = LigneDevisSerializer
    queryset = LigneDevis.objects.none()

    def get_queryset(self):
        return LigneDevis.objects.filter(devis__user=self.request.user)
