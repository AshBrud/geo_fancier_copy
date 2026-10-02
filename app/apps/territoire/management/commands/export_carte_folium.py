import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from territoire.models import Batiment, Espace


class Command(BaseCommand):
    help = "Genere une carte HTML Folium depuis les espaces et batiments en base."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="donnees/carte_campus_folium.html",
            help="Chemin du fichier HTML a generer.",
        )
        parser.add_argument("--lat", type=float, default=14.696291168874254)
        parser.add_argument("--lng", type=float, default=-16.477368387258974)
        parser.add_argument("--zoom", type=int, default=17)

    def handle(self, *args, **options):
        try:
            import folium
        except ImportError as exc:
            raise CommandError(
                "Folium n'est pas installe. Installez-le avec: "
                ".\\venv\\Scripts\\pip install folium"
            ) from exc

        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)

        m = folium.Map(
            location=[options["lat"], options["lng"]],
            zoom_start=options["zoom"],
            tiles="OpenStreetMap",
        )

        espaces_group = folium.FeatureGroup(name="Espaces fonciers", show=True)
        for espace in Espace.objects.all():
            feature = {
                "type": "Feature",
                "geometry": json.loads(espace.geometrie.geojson),
                "properties": {
                    "nom": espace.nom,
                    "code": espace.code,
                    "type": espace.get_type_espace_display(),
                    "superficie": espace.superficie,
                    "usage": espace.usage,
                },
            }
            folium.GeoJson(
                feature,
                name=espace.code,
                style_function=lambda feature, color=espace.couleur: {
                    "fillColor": color,
                    "color": "#ffffff",
                    "weight": 1.5,
                    "fillOpacity": 0.55,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=["nom", "code", "type", "superficie"],
                    aliases=["Nom", "Code", "Type", "Superficie m2"],
                ),
            ).add_to(espaces_group)
        espaces_group.add_to(m)

        batiments_group = folium.FeatureGroup(name="Batiments", show=True)
        for batiment in Batiment.objects.filter(est_actif=True).select_related("fonction"):
            feature = {
                "type": "Feature",
                "geometry": json.loads(batiment.geometrie.geojson),
                "properties": {
                    "nom": batiment.nom,
                    "code": batiment.code,
                    "fonction": batiment.fonction.nom if batiment.fonction else "",
                    "superficie": batiment.superficie,
                    "etages": batiment.etages,
                },
            }
            folium.GeoJson(
                feature,
                name=batiment.code,
                style_function=lambda feature: {
                    "fillColor": "#1E3A8A",
                    "color": "#ffffff",
                    "weight": 1.5,
                    "fillOpacity": 0.7,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=["nom", "code", "fonction", "etages", "superficie"],
                    aliases=["Nom", "Code", "Fonction", "Etages", "Superficie m2"],
                ),
            ).add_to(batiments_group)
        batiments_group.add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)
        m.save(str(output))

        self.stdout.write(self.style.SUCCESS(f"Carte Folium generee: {output}"))
