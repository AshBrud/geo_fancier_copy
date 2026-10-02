from django.db import migrations, models


def migrer_statuts(apps, schema_editor):
    NouvelleConstruction = apps.get_model('urbanisme', 'NouvelleConstruction')
    # 'attente' → 'en_cours' (nouvelle demande = en cours de traitement)
    NouvelleConstruction.objects.filter(statut='attente').update(statut='en_cours')
    # 'terminee' → 'approuvee' (projet terminé = approuvé)
    NouvelleConstruction.objects.filter(statut='terminee').update(statut='approuvee')


class Migration(migrations.Migration):

    dependencies = [
        ('urbanisme', '0002_add_espace_souhaitee_fk'),
    ]

    operations = [
        migrations.RunPython(migrer_statuts, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='nouvelleconstruction',
            name='statut',
            field=models.CharField(
                choices=[
                    ('en_cours', 'En cours'),
                    ('approuvee', 'Approuvée'),
                    ('rejetee', 'Rejetée'),
                ],
                default='en_cours',
                max_length=20,
            ),
        ),
    ]
