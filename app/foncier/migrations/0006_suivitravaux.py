import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foncier', '0005_supprime_capacite_batiment'),
        ('constructions', '0003_simplifier_statuts'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SuiviTravaux',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('statut', models.CharField(
                    choices=[('non_demarre', 'Non démarré'), ('en_cours', 'En cours'), ('termine', 'Terminé')],
                    default='non_demarre', max_length=20, verbose_name='Statut des travaux',
                )),
                ('date_debut', models.DateField(blank=True, null=True, verbose_name='Date de début')),
                ('date_fin_prevue', models.DateField(blank=True, null=True, verbose_name='Date de fin prévue')),
                ('observations', models.TextField(blank=True, verbose_name='Observations')),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('date_modification', models.DateTimeField(auto_now=True)),
                ('construction', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='suivi',
                    to='constructions.nouvelleconstruction',
                    verbose_name='Demande de construction',
                )),
                ('maitre_ouvrage', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='travaux_diriges',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Maître d'ouvrage",
                )),
            ],
            options={
                'verbose_name': 'Suivi des travaux',
                'verbose_name_plural': 'Suivis des travaux',
                'ordering': ['-date_creation'],
            },
        ),
    ]
