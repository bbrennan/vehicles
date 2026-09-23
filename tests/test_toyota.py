import tempfile
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from unittest.mock import patch

from vehicle_catalog.pipeline import encode, write_once
from vehicle_catalog.layout import parse_layout
from vehicle_catalog.toyota import (
    BASE,
    STEMS,
    BrochureLinks,
    download,
    source_for,
)


class ToyotaTests(unittest.TestCase):
    def test_pattern_source_ids_are_unique(self):
        identifiers = [
            source_for(f"{BASE}2015/{stem}_ebrochure.pdf").id for stem in STEMS
        ]
        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_success_extraction_failure_and_access_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = root / "inventory.json"
            write_once(
                inventory,
                encode(
                    {
                        "market": "US",
                        "make": "Toyota",
                        "documents": [
                            {"url": BASE + "2026/camry.pdf"},
                            {"url": BASE + "2026/corolla.pdf"},
                        ],
                    }
                ),
            )
            with (
                patch("vehicle_catalog.toyota.fetch") as retrieve,
                patch(
                    "vehicle_catalog.toyota.link_pdf",
                    side_effect=lambda artifact, raw: raw / "pdfs/example.pdf",
                ),
                patch("vehicle_catalog.toyota.extract_pdf") as extract,
            ):
                retrieve.return_value = SimpleNamespace(id="synthetic")
                extract.side_effect = [
                    {"page_count": 2},
                    subprocess.TimeoutExpired("pdf", 60),
                ]
                report = download(inventory, root, "extract", 2)
                self.assertEqual(report["acquired"], 2)
                self.assertEqual(report["extracted"], 1)
                self.assertIn("TimeoutExpired", report["results"][1]["error"])
                self.assertEqual(
                    retrieve.call_args.kwargs["max_bytes"], 100 * 1024 * 1024
                )
                retrieve.reset_mock()
                retrieve.side_effect = HTTPError(
                    BASE, 429, "rate limit", {}, None
                )
                report = download(inventory, root, "blocked", 2)
                retrieve.assert_called_once()
                self.assertEqual(
                    report["results"][1]["acquisition"], "not_attempted"
                )

    def test_raw_layout_preserves_coordinates_and_blank_pages(self):
        payload = b"""<html xmlns="http://www.w3.org/1999/xhtml"><doc>
        <page width="612" height="792"><flow>
        <block xMin="1" yMin="2" xMax="30" yMax="40">
        <line xMin="1" yMin="2" xMax="30" yMax="40">
        <word xMin="1" yMin="2" xMax="10" yMax="12">LE</word>
        <word xMin="20" yMin="2" xMax="30" yMax="12">S</word>
        </line></block></flow></page><page width="612" height="792"/>
        </doc></html>"""
        pages = parse_layout(payload)
        self.assertEqual(len(pages), 2)
        words = pages[0]["blocks"][0]["lines"][0]["words"]
        self.assertEqual(words[0]["text"], "LE")
        self.assertEqual(words[1]["bbox"]["xMin"], 20)
        self.assertEqual(pages[1]["blocks"], [])
        repaired = parse_layout(payload.replace(b">LE<", b">\x01LE<"))
        self.assertEqual(
            repaired[0]["blocks"][0]["lines"][0]["words"][0]["text"],
            "\ufffdLE",
        )
        with self.assertRaises(ValueError):
            parse_layout(b"<doc/>")
        with self.assertRaises(ValueError):
            parse_layout(payload.replace(b'xMin="1"', b'xMin="NaN"'))

    def test_links_only_first_party_pdfs(self):
        parser = BrochureLinks()
        parser.feed(
            f'<a href="{BASE}2026/camry.pdf">PDF</a>'
            '<a href="https://example.com/other.pdf">Other</a>'
            '<a href="/brochures/trucks/">Trucks</a>'
        )
        self.assertEqual(parser.links, {BASE + "2026/camry.pdf"})
        self.assertEqual(source_for(BASE + "2026/camry.pdf").market, "US")
        for url in (
            "https://example.com/other.pdf",
            BASE + "x.pdf?token=x",
            "http://www.toyota.com/brochures/trucks/",
        ):
            with self.assertRaises(ValueError):
                source_for(url)

    def test_download_budget_and_failure_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = root / "inventory.json"
            write_once(
                inventory,
                encode(
                    {
                        "market": "US",
                        "make": "Toyota",
                        "documents": [
                            {
                                "url": BASE + "2015/camry_ebrochure.pdf",
                                "discovery": "unverified_url_pattern",
                            }
                        ],
                    }
                ),
            )
            with patch(
                "vehicle_catalog.toyota.fetch", side_effect=OSError("404")
            ) as retrieve:
                with self.assertRaises(ValueError):
                    download(inventory, root, "blocked", 0)
                retrieve.assert_not_called()
                report = download(inventory, root, "test", 1)
                self.assertEqual(report["acquired"], 0)
                self.assertFalse(report["complete"])
                self.assertIn("404", report["results"][0]["error"])
                self.assertTrue(
                    (root / "staged/test/events/0001.json").exists()
                )
                with self.assertRaisesRegex(ValueError, "already exists"):
                    download(inventory, root, "test", 1)
