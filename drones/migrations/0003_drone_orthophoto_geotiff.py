from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drones', '0002_missiondrone_tiles_url'),
    ]

    operations = [
        # MissionDrone : ajout du champ d'import KML/KMZ/GPX
        migrations.AddField(
            model_name='missiondrone',
            name='fichier_kml',
            field=models.FileField(
                blank=True, null=True,
                upload_to='missions/kml/',
                verbose_name='Fichier KML/KMZ/GPX',
                help_text='Importer automatiquement la zone couverte depuis un fichier KML, KMZ ou GPX',
            ),
        ),
        # Orthophoto : ImageField → FileField (supporte GeoTIFF)
        migrations.AlterField(
            model_name='orthophoto',
            name='fichier',
            field=models.FileField(upload_to='orthophotos/', verbose_name='Fichier (GeoTIFF, PNG, JPEG)'),
        ),
        # Orthophoto : nouveaux champs auto-extraits
        migrations.AddField(
            model_name='orthophoto',
            name='systeme_proj',
            field=models.CharField(blank=True, max_length=200, verbose_name='Système de projection'),
        ),
        migrations.AddField(
            model_name='orthophoto',
            name='largeur_px',
            field=models.IntegerField(blank=True, null=True, verbose_name='Largeur (px)'),
        ),
        migrations.AddField(
            model_name='orthophoto',
            name='hauteur_px',
            field=models.IntegerField(blank=True, null=True, verbose_name='Hauteur (px)'),
        ),
    ]
