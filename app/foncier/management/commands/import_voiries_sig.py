from django.core.management.base import BaseCommand, CommandError

from foncier.models import Voirie

from ._sig_import import first_existing, geometry_to_multilinestring, read_layer


class Command(BaseCommand):
    help = "Importe des voiries depuis un GeoJSON/Shapefile/GeoPackage avec GeoPandas."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Chemin du fichier SIG a importer.")
        parser.add_argument("--layer", help="Nom de la couche a lire (GeoPackage multi-couches).")
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
        gdf = read_layer(options["path"], source_crs=options.get("source_crs"), layer=options.get("layer"))

        created = 0
        updated = 0
        skipped = 0

        for index, row in gdf.iterrows():
            nom = first_existing(row, ["nom", "NOM", "name", "NAME", "libelle"])
            type_voirie = first_existing(row, ["type", "TYPE", "type_voirie"], "")
            revetement = first_existing(row, ["revetement", "REVETEMENT", "revêtement"], "")
            etat = first_existing(row, ["etat", "ETAT", "état"], "")
            observation = first_existing(row, ["observation", "OBSERVATION", "obs"], "")

            if not nom:
                skipped += 1
                self.stderr.write(f"Ligne {index}: ignoree, nom manquant.")
                continue

            geom = geometry_to_multilinestring(row.geometry)
            if geom is None:
                skipped += 1
                self.stderr.write(f"Ligne {index} ({nom}): geometrie lineaire invalide.")
                continue

            if options["dry_run"]:
                created += 1
                continue

            _obj, was_created = Voirie.objects.update_or_create(
                nom=nom,
                defaults={
                    "type_voirie": type_voirie,
                    "revetement": revetement,
                    "etat": etat,
                    "observation": observation,
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
