from django.db import migrations
from django.utils import timezone


def rattacher_mission_heritee(apps, schema_editor):
    Mission = apps.get_model('drones', 'Mission')
    Orthophoto = apps.get_model('drones', 'Orthophoto')

    orthos_orphelines = Orthophoto.objects.filter(mission__isnull=True)
    if not orthos_orphelines.exists():
        return

    mission = Mission.objects.create(
        nom="Données antérieures (import automatique)",
        date_vol=timezone.now().date(),
        operateur="Migration",
        statut='integree',
        notes="Mission générée automatiquement pour conserver la visibilité des orthophotos "
              "importées avant l'introduction du workflow de missions de vol.",
    )
    orthos_orphelines.update(mission=mission, valide=True, date_validation=timezone.now())


def revenir_en_arriere(apps, schema_editor):
    Mission = apps.get_model('drones', 'Mission')
    Mission.objects.filter(nom="Données antérieures (import automatique)").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('drones', '0007_mission_orthophoto_date_validation_and_more'),
    ]

    operations = [
        migrations.RunPython(rattacher_mission_heritee, revenir_en_arriere),
    ]
