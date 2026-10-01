from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drones', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='missiondrone',
            name='tiles_url',
            field=models.CharField(
                blank=True,
                help_text='Format : /static/tiles/mission/{z}/{x}/{y}.png ou URL WebODM',
                max_length=500,
                verbose_name='URL tuiles XYZ (WebODM)',
            ),
        ),
    ]
