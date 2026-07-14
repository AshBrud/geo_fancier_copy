from django.core.management.base import BaseCommand, CommandError

from foncier.models import Espace

from ._sig_import import (
    clamp_taux_occupation,
    first_existing,
    geometry_to_multipolygon,
    normalize_type_espace,
    read_layer,
)


class Command(BaseCommand):
    help = "Importe des espaces fonciers depuis un GeoJSON/Shapefile avec GeoPandas."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Chemin du fichier GeoJSON/Shapefile a importer.")
        parser.add_argument(
            "--source-crs",
            help="CRS source si le fichier n'en contient pas, ex: EPSG:32628.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Valide le fichier sans ecrire en base.",
        )

    def handle(self, *args, **options):
        gdf = read_layer(options["path"], source_crs=options.get("source_crs"))

        created = 0
        updated = 0
        skipped = 0

        valid_types = {key for key, _label in Espace.TYPES}

        for index, row in gdf.iterrows():
            code = first_existing(row, ["code", "CODE", "id", "ID"])
            nom = first_existing(row, ["nom", "NOM", "name", "NAME", "libelle"], code)
            type_espace = normalize_type_espace(
                first_existing(row, ["type_espace", "TYPE_ESPACE", "type", "TYPE", "statut"], "libre")
            )
            usage = first_existing(row, ["usage", "USAGE", "occupation"], "")
            description = first_existing(row, ["description", "DESCRIPTION", "desc"], "")
            taux_occupation = clamp_taux_occupation(
                first_existing(row, ["taux_occupation", "TAUX_OCCUPATION", "taux", "TAUX"], "60")
            )

            if not code:
                skipped += 1
                self.stderr.write(f"Ligne {index}: ignoree, code manquant.")
                continue
            if type_espace not in valid_types:
                skipped += 1
                self.stderr.write(
                    f"Ligne {index} ({code}): type_espace invalide '{type_espace}'."
                )
                continue

            geom = geometry_to_multipolygon(row.geometry)
            if geom is None:
                skipped += 1
                self.stderr.write(f"Ligne {index} ({code}): geometrie polygonale invalide.")
                continue

            if options["dry_run"]:
                created += 1
                continue

            _obj, was_created = Espace.objects.update_or_create(
                code=code,
                defaults={
                    "nom": nom or code,
                    "type_espace": type_espace,
                    "usage": usage,
                    "description": description,
                    "taux_occupation": taux_occupation,
                    "geometrie": geom,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        if skipped and not created and not updated:
            raise CommandError("Aucune entite valide n'a ete importee.")

        mode = "validation" if options["dry_run"] else "import"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode} termine: {created} cree(s), {updated} mis a jour, {skipped} ignore(s)."
            )
        )
