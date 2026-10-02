from django.db import migrations


FONCTIONS = [
    "Amphithéâtre",
    "Salle de cours",
    "Bureau administratif",
    "Laboratoire",
    "Bibliothèque / Médiathèque",
    "Résidence universitaire",
    "Restaurant universitaire",
    "Infirmerie / Centre de santé",
    "Salle informatique",
    "Direction / Rectorat",
    "Service technique",
    "Gymnase / Salle de sport",
    "Mosquée",
    "Parking / Aire de stationnement",
    "Entrepôt / Magasin",
    "Salle de conférence",
    "Centre de recherche",
]


def add_fonctions(apps, schema_editor):
    FonctionBatiment = apps.get_model('territoire', 'FonctionBatiment')
    for nom in FONCTIONS:
        FonctionBatiment.objects.get_or_create(nom=nom)


def remove_fonctions(apps, schema_editor):
    FonctionBatiment = apps.get_model('territoire', 'FonctionBatiment')
    FonctionBatiment.objects.filter(nom__in=FONCTIONS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('territoire', '0002_remove_types_vert_sportif'),
    ]

    operations = [
        migrations.RunPython(add_fonctions, remove_fonctions),
    ]
