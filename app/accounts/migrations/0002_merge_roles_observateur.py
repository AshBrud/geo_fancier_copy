from django.db import migrations, models


def migrer_anciens_roles(apps, schema_editor):
    """Migre etudiant / enseignant / visiteur → observateur."""
    CustomUser = apps.get_model('accounts', 'CustomUser')
    CustomUser.objects.filter(
        role__in=['etudiant', 'enseignant', 'visiteur']
    ).update(role='observateur')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        # 1. Mettre à jour les choix et la valeur par défaut
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                choices=[
                    ('admin', 'Administrateur'),
                    ('domaine_foncier', 'Responsable Domaine Foncier'),
                    ('administration', 'Administration Universitaire'),
                    ('observateur', 'Observateur UAD'),
                ],
                default='observateur',
                max_length=20,
            ),
        ),
        # 2. Migrer les utilisateurs avec les anciens rôles
        migrations.RunPython(migrer_anciens_roles, migrations.RunPython.noop),
    ]
