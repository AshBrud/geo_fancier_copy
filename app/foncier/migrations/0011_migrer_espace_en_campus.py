from django.db import migrations


def migrer_espace_en_campus(apps, schema_editor):
    """
    Avant cette migration, le périmètre d'étude était représenté par un
    Espace ordinaire (type 'libre'). Ce modèle introduit un Campus dédié,
    qui ne doit jamais être un espace parmi d'autres : on convertit donc
    l'espace le plus grand existant en Campus, et on le supprime de la
    table Espace pour éviter tout double comptage dans les statistiques.
    """
    Espace = apps.get_model('foncier', 'Espace')
    Campus = apps.get_model('foncier', 'Campus')

    if Campus.objects.exists():
        return

    plus_grand = Espace.objects.order_by('-superficie').first()
    if not plus_grand:
        return

    Campus.objects.create(
        nom=plus_grand.nom or 'Campus UAD Bambey',
        geometrie=plus_grand.geometrie,
        superficie=plus_grand.superficie,
        description=plus_grand.description,
    )
    plus_grand.delete()


def revenir_en_arriere(apps, schema_editor):
    """Pas de retour automatique : recréer manuellement l'espace si besoin."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('foncier', '0010_campus_espace_campus'),
    ]

    operations = [
        migrations.RunPython(migrer_espace_en_campus, revenir_en_arriere),
    ]
