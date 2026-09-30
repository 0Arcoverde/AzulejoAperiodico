import json
import math
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import gerar_azulejo as gerador


ROOT = Path(__file__).resolve().parents[1]
SVG_NS = "{http://www.w3.org/2000/svg}"


class ArquivoGeradoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.svg_path = Path(cls.temp_dir.name) / "hat-64.svg"
        subprocess.run(
            (
                sys.executable,
                str(ROOT / "gerar_azulejo.py"),
                "--tile",
                "hat",
                "--size-cm",
                "5",
                "--count",
                "64",
                "--output",
                str(cls.svg_path),
            ),
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        cls.root = ET.parse(cls.svg_path).getroot()
        metadata_element = cls.root.find(SVG_NS + "metadata")
        cls.metadata = json.loads(metadata_element.text)
        cls.cut_group = cls.root.find(f"{SVG_NS}g[@id='cut-lines']")
        cls.paths = cls.cut_group.findall(SVG_NS + "path")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_metatiles_expand_to_connected_nonoverlapping_hats(self):
        expected_sizes = {"T": 1, "H": 4, "P": 2, "F": 2}
        for kind, expected_size in expected_sizes.items():
            with self.subTest(kind=kind):
                transforms = gerador.metatile_transforms(kind)
                self.assertEqual(len(transforms), expected_size)
                cells = gerador.metatile_cells(kind)
                self.assertEqual(len(cells), expected_size * len(gerador.HAT_KITES))
                self.assertTrue(gerador.is_simply_connected(cells))

    def test_svg_contains_requested_tiles_and_metadata(self):
        self.assertEqual(self.metadata["schema"], "hat-metatile-patch-v1")
        self.assertEqual(self.metadata["count"], 64)
        self.assertEqual(len(self.metadata["transforms"]), 64)
        self.assertEqual(len(self.metadata["placements"]), 64)
        self.assertTrue(self.root.attrib["width"].endswith("mm"))
        self.assertTrue(self.root.attrib["height"].endswith("mm"))

    def test_svg_contains_one_filled_face_per_tile_under_cut_lines(self):
        fill_group = self.root.find(f"{SVG_NS}g[@id='tile-fills']")
        fill_paths = fill_group.findall(SVG_NS + "path")
        self.assertEqual(fill_group.attrib["fill"], "#e6e6e6")
        self.assertEqual(len(fill_paths), self.metadata["count"])
        self.assertTrue(all(path.attrib["d"].endswith(" Z") for path in fill_paths))
        groups = self.root.findall(SVG_NS + "g")
        self.assertLess(groups.index(fill_group), groups.index(self.cut_group))

    def test_tiles_do_not_overlap_and_patch_has_no_holes(self):
        occupied = set()
        for raw_transform in self.metadata["transforms"]:
            transform = tuple(raw_transform)
            cells = gerador.transformed_hat_cells(transform)
            self.assertTrue(occupied.isdisjoint(cells))
            occupied.update(cells)
        self.assertEqual(len(occupied), 64 * len(gerador.HAT_KITES))
        self.assertTrue(gerador.is_simply_connected(occupied))

    def test_complete_neighbourhoods_match_article_metatiles(self):
        transforms = tuple(tuple(row) for row in self.metadata["transforms"])
        valid, checked = gerador.complete_metatile_checks(transforms)
        self.assertTrue(valid)
        self.assertGreater(checked, 0)

    def test_svg_cuts_are_unique_nonzero_segments_inside_sheet(self):
        width = float(self.root.attrib["width"].removesuffix("mm"))
        height = float(self.root.attrib["height"].removesuffix("mm"))
        edges = set()
        actual_edges = set()
        for path in self.paths:
            points = [
                tuple(map(float, match))
                for match in re.findall(r"[ML] ([0-9.]+) ([0-9.]+)", path.attrib["d"])
            ]
            self.assertEqual(len(points), 2)
            start, end = points
            self.assertGreater(math.dist(start, end), 0)
            for x, y in points:
                self.assertGreaterEqual(x, 0)
                self.assertGreaterEqual(y, 0)
                self.assertLessEqual(x, width)
                self.assertLessEqual(y, height)
            edges.add(tuple(sorted(points)))
            actual_edges.add(tuple(sorted(
                tuple(round(value, 3) for value in point)
                for point in points
            )))
        self.assertEqual(len(edges), len(self.paths))
        self.assertLess(len(self.paths), 64 * 13)

        placements = self.metadata["placements"]
        placed_edges = []
        all_points = []
        ratio = self.metadata["ratio"]
        for placement in placements:
            transform = tuple(placement["transform"])
            offset = tuple(placement["offset"])
            _, local_edges = gerador.tile_boundary(transform, ratio)
            for _, _, local_start, local_end in local_edges:
                start = (local_start[0] + offset[0], local_start[1] + offset[1])
                end = (local_end[0] + offset[0], local_end[1] + offset[1])
                placed_edges.append((start, end))
                all_points.extend((start, end))

        min_x = min(x for x, _ in all_points)
        max_y = max(y for _, y in all_points)
        patch_height = max_y - min(y for _, y in all_points)
        scale = self.metadata["scale_mm"]
        offset_x, offset_y = self.metadata["svg_offset_mm"]
        expected_edges = set()
        for start, end in placed_edges:
            normalized = []
            for x, y in (start, end):
                x = round(x - min_x, 6)
                y = round(max_y - y, 6)
                if self.metadata["rotate_patch"]:
                    x, y = patch_height - y, x
                normalized.append((
                    round(x * scale + offset_x, 3),
                    round(y * scale + offset_y, 3),
                ))
            expected_edges.add(tuple(sorted(normalized)))
        self.assertEqual(actual_edges, expected_edges)

    def test_article_fixture_has_all_188_surroundable_patches(self):
        signatures = gerador.valid_metatile_patch_signatures()
        self.assertEqual(len(signatures), 188)
        self.assertIn(
            gerador.metatile_patch_signature(gerador.SURROUNDABLE_SEED, gerador.IDENTITY),
            signatures,
        )

    def test_sheet_generation_reports_progress_to_stderr(self):
        output_path = Path(self.temp_dir.name) / "sheet-progress.svg"
        result = subprocess.run(
            (
                sys.executable,
                str(ROOT / "gerar_azulejo.py"),
                "--tile",
                "hat",
                "--size-cm",
                "5",
                "--sheet-cm",
                "20",
                "20",
                "--progress-interval",
                "0.01",
                "--output",
                str(output_path),
            ),
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertIn("[progresso]", result.stderr)
        self.assertIn("candidatos", result.stderr)
        self.assertIn("fronteira", result.stderr)
        self.assertIn("concluído", result.stderr)
        self.assertTrue(output_path.is_file())

    def test_downloadable_shape_examples_are_valid_50mm_svgs(self):
        examples = (
            "hat-5cm.svg",
            "turtle-5cm.svg",
            "tile-1-1-5cm.svg",
            "spectre-5cm.svg",
        )
        for filename in examples:
            with self.subTest(filename=filename):
                root = ET.parse(ROOT / "exemplos" / filename).getroot()
                paths = root.find(SVG_NS + "g").findall(SVG_NS + "path")
                self.assertEqual(len(paths), 64)
                self.assertTrue(root.attrib["width"].endswith("mm"))
                self.assertTrue(root.attrib["height"].endswith("mm"))
                for path in paths:
                    points = [
                        tuple(map(float, match))
                        for match in re.findall(
                            r"[ML] ([0-9.]+) ([0-9.]+)", path.attrib["d"]
                        )
                    ]
                    self.assertGreater(len(points), 10)
                    widest = max(
                        math.dist(first, second)
                        for index, first in enumerate(points)
                        for second in points[index + 1:]
                    )
                    self.assertAlmostEqual(widest, 50.0, delta=0.01)

    def test_spectre_example_uses_its_published_outline(self):
        root = ET.parse(ROOT / "exemplos" / "spectre-5cm.svg").getroot()
        paths = root.find(SVG_NS + "g").findall(SVG_NS + "path")
        points = [
            tuple(map(float, match))
            for match in re.findall(r"[ML] ([0-9.]+) ([0-9.]+)", paths[0].attrib["d"])
        ]
        self.assertEqual(len(points), len(gerador.SPECTRE_OUTLINE))
        self.assertNotEqual(len(points), len(gerador.HAT_GRID))

    def test_tile_one_one_has_equilateral_edges_not_hat_edge_ratio(self):
        def read_first_tile(filename):
            root = ET.parse(ROOT / "exemplos" / filename).getroot()
            path = root.find(SVG_NS + "g").find(SVG_NS + "path")
            return [
                tuple(map(float, match))
                for match in re.findall(r"[ML] ([0-9.]+) ([0-9.]+)", path.attrib["d"])
            ]

        equilateral = read_first_tile("tile-1-1-5cm.svg")
        hat = read_first_tile("hat-5cm.svg")
        equilateral_sides = [
            math.dist(start, end)
            for start, end in zip(equilateral, equilateral[1:] + equilateral[:1])
        ]
        hat_sides = [
            math.dist(start, end)
            for start, end in zip(hat, hat[1:] + hat[:1])
        ]
        self.assertEqual(len(equilateral_sides), 14)
        self.assertLess(max(equilateral_sides) - min(equilateral_sides), 0.01)
        self.assertGreater(max(hat_sides) / min(hat_sides), 1.7)


if __name__ == "__main__":
    unittest.main()