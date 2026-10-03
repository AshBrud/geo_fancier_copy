# Generated manually for mandatory password change on first login / credential reset

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_customuser_acces_tous_territoires'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='must_change_password',
            field=models.BooleanField(
                default=False,
                help_text="Si activé, l'utilisateur doit obligatoirement définir un nouveau mot de passe lors de sa connexion.",
                verbose_name="Changement de mot de passe obligatoire"
            ),
        ),
    ]
