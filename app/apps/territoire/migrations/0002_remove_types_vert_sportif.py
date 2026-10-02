from django.db import migrations, models


def supprimer_espaces_vert_sportif(apps, schema_editor):
    """Convertit les espaces de type vert/sportif en espace réservé."""
    Espace = apps.get_model('territoire', 'Espace')
    Espace.objects.filter(type_espace__in=['vert', 'sportif']).update(type_espace='reserve')


class Migration(migrations.Migration):

    dependencies = [
        ('territoire', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(supprimer_espaces_vert_sportif, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='espace',
            name='type_espace',
            field=models.CharField(
                choices=[
                    ('libre', 'Espace libre'),
                    ('occupe', 'Espace occupé'),
                    ('reserve', 'Espace réservé'),
                    ('route', 'Route / Voie'),
                ],
                max_length=20,
                verbose_name='Type',
            ),
        ),
    ]
