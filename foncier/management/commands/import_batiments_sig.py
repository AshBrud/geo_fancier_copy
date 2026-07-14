from django.core.management.base import BaseCommand, CommandError

from ._sig_import import sync_batiments


class Command(BaseCommand):
    help = "Importe des batiments depuis un GeoJSON/Shapefile avec GeoPandas."

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
        result = sync_batiments(
            options["path"],
            source_crs=options.get("source_crs"),
            dry_run=options["dry_run"],
        )

        for error in result["errors"]:
            self.stderr.write(error)

        if result["skipped"] and not result["created"] and not result["updated"]:
            raise CommandError("Aucune entite valide n'a ete importee.")

        mode = "validation" if options["dry_run"] else "import"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode} termine: {result['created']} cree(s), {result['updated']} mis a jour, "
                f"{result['skipped']} ignore(s)."
            )
        )
