#!/usr/bin/env python3
"""Gera SVGs de polykites e variantes da família Tile(a, b)."""

import argparse
import hashlib
import json
import math
import sys
import time
from functools import lru_cache
from pathlib import Path


# Contorno hat_outline do código auxiliar de An aperiodic monotile.
HAT_GRID = (
    (0, 0),
    (-1, -1),
    (0, -2),
    (2, -2),
    (2, -1),
    (4, -2),
    (5, -1),
    (4, 0),
    (3, 0),
    (2, 2),
    (0, 3),
    (0, 2),
    (-1, 2),
)
HAT_KITES = {
    (0, -1), (1, -1), (1, 0), (0, 1),
    (1, 2), (2, 1), (3, -1), (4, -1),
}
SQRT3 = math.sqrt(3)
SPECTRE_OUTLINE = (
    (0, 0),
    (1, 0),
    (1.5, -SQRT3 / 2),
    (1.5 + SQRT3 / 2, 0.5 - SQRT3 / 2),
    (1.5 + SQRT3 / 2, 1.5 - SQRT3 / 2),
    (2.5 + SQRT3 / 2, 1.5 - SQRT3 / 2),
    (3 + SQRT3 / 2, 1.5),
    (3, 2),
    (3 - SQRT3 / 2, 1.5),
    (2.5 - SQRT3 / 2, 1.5 + SQRT3 / 2),
    (1.5 - SQRT3 / 2, 1.5 + SQRT3 / 2),
    (0.5 - SQRT3 / 2, 1.5 + SQRT3 / 2),
    (-SQRT3 / 2, 1.5),
    (0, 1),
)
IDENTITY = (1, 0, 0, 0, 1, 0)
ROTATE_60 = (0, -1, 0, 1, 1, 0)
REFLECT_X = (1, 1, 0, 0, -1, 0)
SURROUNDABLE_SEED = (
    IDENTITY,
    (0, -1, -2, -1, 0, 4),
    (-1, 0, -2, 1, 1, -2),
    (-1, -1, 2, 0, 1, -4),
    (0, -1, 4, -1, 0, -2),
    (1, 0, 6, -1, -1, 0),
    (1, 1, 2, 0, -1, 2),
    (1, 1, -8, 0, -1, 4),
    (1, 0, -12, -1, -1, 6),
    (-1, -1, -6, 0, 1, 0),
    (1, 0, -4, -1, -1, -4),
    (0, 1, 2, 1, 0, -10),
    (1, 1, 4, 0, -1, -8),
    (0, -1, 8, -1, 0, -4),
    (1, 1, 12, 0, -1, -6),
    (1, 1, 10, 0, -1, -2),
    (-1, 0, 8, 1, 1, 2),
    (1, 1, 0, 0, -1, 6),
    (1, 0, -4, -1, -1, 8),
    (-1, -1, -6, 1, 0, 6),
)
METATILE_HASHES = Path(__file__).parent / "referencias" / "hat-2patch-hashes.txt"

DEFAULT_RATIOS = {
    "hat": math.sqrt(3),
    "turtle": 1 / math.sqrt(3),
    "equilateral": 1.0,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Gera contornos de tiles em SVG para corte a laser."
    )
    parser.add_argument("-o", "--output", default="azulejos.svg")
    parser.add_argument("--count", type=int)
    parser.add_argument(
        "--sheet-cm",
        nargs=2,
        type=float,
        metavar=("LARGURA", "ALTURA"),
        help="Dimensões da chapa em centímetros; gera automaticamente o maior patch encontrado.",
    )
    parser.add_argument(
        "--margin-mm",
        type=float,
        default=5.0,
        help="Margem livre ao redor do patch em modo chapa (padrão: 5 mm).",
    )
    parser.add_argument(
        "--progress-interval",
        type=float,
        default=2.0,
        help="Intervalo em segundos entre logs de progresso (padrão: 2).",
    )
    parser.add_argument("--columns", type=int, default=1)
    parser.add_argument(
        "--layout",
        choices=("tiling", "array"),
        default="tiling",
        help="Patch compacto do ladrilhamento ou peças em grade retangular.",
    )
    parser.add_argument(
        "--tile",
        choices=("hat", "turtle", "equilateral", "spectre", "family"),
        default="hat",
        help="Hat, Turtle, Tile(1,1), Spectre ou proporção livre.",
    )
    parser.add_argument(
        "--ratio",
        type=float,
        help="r=b/a para Tile(a,b); válido com family ou --grid-json.",
    )
    parser.add_argument(
        "--grid-json",
        help="JSON com vértices [x,y] em coordenadas axiais da grade triangular.",
    )
    size = parser.add_mutually_exclusive_group()
    size.add_argument(
        "--size-cm",
        type=float,
        help="Diâmetro ponta a ponta da peça em centímetros (padrão: 5).",
    )
    size.add_argument(
        "--module-mm",
        type=float,
        help="Escala alternativa: mm por unidade dos lados de comprimento 1.",
    )
    parser.add_argument(
        "--gap-mm",
        type=float,
        default=5.0,
        help="Espaço entre peças no arquivo (padrão: 5 mm).",
    )
    args = parser.parse_args()
    if args.count is not None and args.count < 1:
        parser.error("--count deve ser pelo menos 1")
    if args.count is not None and args.sheet_cm is not None:
        parser.error("use --count ou --sheet-cm, não ambos")
    if args.sheet_cm is not None and min(args.sheet_cm) <= 0:
        parser.error("as dimensões de --sheet-cm devem ser maiores que zero")
    if args.columns < 1:
        parser.error("--columns deve ser pelo menos 1")
    if args.size_cm is not None and args.size_cm <= 0:
        parser.error("--size-cm deve ser maior que zero")
    if args.module_mm is not None and args.module_mm <= 0:
        parser.error("--module-mm deve ser maior que zero")
    if args.gap_mm < 0:
        parser.error("--gap-mm não pode ser negativo")
    if args.margin_mm < 0:
        parser.error("--margin-mm não pode ser negativo")
    if args.progress_interval <= 0:
        parser.error("--progress-interval deve ser maior que zero")
    if args.ratio is not None and args.ratio <= 0:
        parser.error("--ratio deve ser maior que zero")
    if args.tile == "family" and args.ratio is None:
        parser.error("--tile family requer --ratio")
    if args.ratio is not None and args.tile not in ("family", "hat") and not args.grid_json:
        parser.error("--ratio exige --tile family ou --grid-json")
    if args.tile == "spectre" and args.ratio not in (None, 1, 1.0):
        parser.error("Spectre é construído sobre Tile(1,1); não aceite outro --ratio")
    if args.layout == "tiling" and (args.tile == "spectre" or args.grid_json):
        parser.error("--layout tiling requer Hat, Turtle ou Tile(a,b) da grade do artigo")
    if args.sheet_cm is None and args.count is None:
        args.count = 1
    if args.sheet_cm is not None and args.layout == "array" and args.tile in (
        "hat", "turtle", "equilateral", "family"
    ) and args.ratio is None:
        args.ratio = DEFAULT_RATIOS.get(args.tile, 1.0)
    return args


def load_grid(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        vertices = data["vertices"] if isinstance(data, dict) else data
        points = [tuple(point) for point in vertices]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise ValueError("use JSON válido com uma lista 'vertices' de pares [x,y]") from error
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    if len(points) < 3 or any(len(point) != 2 for point in points):
        raise ValueError("a grade precisa de ao menos três vértices [x,y]")
    if any(
        not isinstance(value, (int, float)) or not math.isfinite(value)
        or not float(value).is_integer()
        for point in points
        for value in point
    ):
        raise ValueError("as coordenadas da grade devem ser inteiros finitos")
    if len(set(points)) != len(points):
        raise ValueError("a grade não pode repetir vértices")
    return points


def grid_edges(points, ratio):
    segments = []
    for start, end in zip(points, points[1:] + points[:1]):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length_squared = dx * dx + dx * dy + dy * dy
        if math.isclose(length_squared, 1, abs_tol=1e-9):
            factor = 1.0
        elif math.isclose(length_squared, 3, abs_tol=1e-9):
            factor = ratio
        elif math.isclose(length_squared, 4, abs_tol=1e-9):
            factor = 1.0
        else:
            raise ValueError(
                "cada lado da grade deve medir 1, √3 ou 2 unidades axiais"
            )
        vector = (dx + dy / 2, dy * math.sqrt(3) / 2)
        if math.isclose(length_squared, 3, abs_tol=1e-9):
            factor = ratio / math.sqrt(3)
        segment = (vector[0] * factor, vector[1] * factor)
        if math.isclose(length_squared, 4, abs_tol=1e-9):
            segments.extend(((segment[0] / 2, segment[1] / 2),) * 2)
        else:
            segments.append(segment)

    closure_x = sum(dx for dx, _ in segments)
    closure_y = sum(dy for _, dy in segments)
    if math.hypot(closure_x, closure_y) > 1e-7:
        raise ValueError("essa proporção não fecha o contorno da grade")
    return segments


def points_from_segments(segments):
    points = [(0.0, 0.0)]
    x = y = 0.0
    for dx, dy in segments:
        x += dx
        y += dy
        points.append((x, y))
    return points[:-1]


def diameter(points):
    return max(
        math.hypot(x1 - x2, y1 - y2)
        for index, (x1, y1) in enumerate(points)
        for x2, y2 in points[index + 1:]
    )


def polygon_area(points):
    return abs(sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
    )) / 2


def transform_point(transform, point):
    a, b, c, d, e, f = transform
    x, y = point
    return a * x + b * y + c, d * x + e * y + f


def compose_transforms(first, second):
    a, b, c, d, e, f = first
    g, h, i, j, k, ell = second
    return (
        a * g + b * j,
        a * h + b * k,
        a * i + b * ell + c,
        d * g + e * j,
        d * h + e * k,
        d * i + e * ell + f,
    )


def add_points(first, second):
    return first[0] + second[0], first[1] + second[1]


def subtract_points(first, second):
    return first[0] - second[0], first[1] - second[1]


def scale_point(point, amount):
    return point[0] * amount, point[1] * amount


def sixfold_centre(point):
    x, y = point
    offsets = (
        (None, (-1, 0), None, None, None, (1, 0)),
        (None, (0, 1), (-1, 1), None, (1, -1), (0, -1)),
    )
    return add_points(point, offsets[y % 2][(x - y) % 6])


def adjacent_kites(point):
    centre = sixfold_centre(point)
    vector = subtract_points(point, centre)
    left = transform_point(ROTATE_60, vector)
    right = transform_point((1, 1, 0, -1, 0, 0), vector)
    return {
        add_points(centre, left),
        add_points(centre, right),
        add_points(point, add_points(vector, left)),
        add_points(point, add_points(vector, right)),
    }


def neighbouring_kites(point):
    centre = sixfold_centre(point)
    vector = subtract_points(point, centre)
    left = transform_point(ROTATE_60, vector)
    right = transform_point((1, 1, 0, -1, 0, 0), vector)
    return (
        add_points(centre, left),
        subtract_points(centre, right),
        subtract_points(centre, vector),
        subtract_points(centre, left),
        add_points(centre, right),
        add_points(point, scale_point(right, 2)),
        add_points(point, add_points(vector, right)),
        add_points(point, add_points(vector, left)),
        add_points(point, scale_point(left, 2)),
    )


def kite_halo(shape):
    return {
        neighbour
        for point in shape
        for neighbour in neighbouring_kites(point)
    } - shape


def is_simply_connected(shape):
    halo = kite_halo(shape)
    if not halo:
        return False
    visited = {next(iter(halo))}
    work = list(visited)
    while work:
        point = work.pop()
        for neighbour in adjacent_kites(point) & halo:
            if neighbour not in visited:
                visited.add(neighbour)
                work.append(neighbour)
    return len(visited) == len(halo)


@lru_cache(maxsize=1)
def legal_neighbour_transforms():
    reflection = REFLECT_X
    rotate = IDENTITY
    orientations = []
    for _ in range(6):
        orientations.extend((rotate, compose_transforms(reflection, rotate)))
        rotate = compose_transforms(ROTATE_60, rotate)

    halo = kite_halo(HAT_KITES)
    neighbours = set()
    for orientation in orientations:
        oriented_cells = {
            transform_point(orientation, point) for point in HAT_KITES
        }
        for halo_point in halo:
            for oriented_point in oriented_cells:
                if subtract_points(
                    oriented_point, sixfold_centre(oriented_point)
                ) != subtract_points(halo_point, sixfold_centre(halo_point)):
                    continue
                offset = subtract_points(halo_point, oriented_point)
                candidate = {
                    add_points(point, offset) for point in oriented_cells
                }
                if candidate & HAT_KITES:
                    continue
                if not is_simply_connected(HAT_KITES | candidate):
                    continue
                translation = (1, 0, offset[0], 0, 1, offset[1])
                neighbours.add(compose_transforms(translation, orientation))
    return tuple(sorted(neighbours))


def inverse_transform(transform):
    a, b, c, d, e, f = transform
    determinant = a * e - b * d
    if abs(determinant) != 1:
        raise ValueError("transformação de tile não é uma simetria da grade")
    inverse = (
        e // determinant,
        -b // determinant,
        (b * f - e * c) // determinant,
        -d // determinant,
        a // determinant,
        (d * c - a * f) // determinant,
    )
    return inverse


def metatile_patch_signature(transforms, centre):
    inverse = inverse_transform(centre)
    relative = sorted(compose_transforms(inverse, transform) for transform in transforms)
    payload = ";".join(",".join(map(str, transform)) for transform in relative)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()[:20]


@lru_cache(maxsize=1)
def valid_metatile_patch_signatures():
    return frozenset(
        line.strip()
        for line in METATILE_HASHES.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def complete_metatile_checks(transforms, focus=None):
    patch = set(transforms)
    neighbours = legal_neighbour_transforms()
    if focus is None:
        centres = patch
    else:
        centres = {focus}
        first_ring = {
            compose_transforms(focus, neighbour)
            for neighbour in neighbours
            if compose_transforms(focus, neighbour) in patch
        }
        centres.update(first_ring)
        for tile in first_ring:
            centres.update(
                compose_transforms(tile, neighbour)
                for neighbour in neighbours
                if compose_transforms(tile, neighbour) in patch
            )

    valid_signatures = valid_metatile_patch_signatures()
    checks = 0
    for centre in centres:
        first_ring = {
            compose_transforms(centre, neighbour)
            for neighbour in neighbours
            if compose_transforms(centre, neighbour) in patch
        }
        second_ring = {
            compose_transforms(tile, neighbour)
            for tile in first_ring
            for neighbour in neighbours
            if compose_transforms(tile, neighbour) in patch
        } - first_ring - {centre}
        neighbourhood = first_ring | second_ring | {centre}
        if len(neighbourhood) != 20:
            continue
        checks += 1
        if metatile_patch_signature(neighbourhood, centre) not in valid_signatures:
            return False, checks
    return True, checks


@lru_cache(maxsize=None)
def transformed_hat_cells(transform):
    return frozenset(transform_point(transform, point) for point in HAT_KITES)


@lru_cache(maxsize=None)
def tile_boundary(transform, ratio):
    axial = [transform_point(transform, point) for point in HAT_GRID]
    points = [(0.0, 0.0)]
    edges = []
    x = y = 0.0
    for start, end in zip(axial, axial[1:] + axial[:1]):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length_squared = dx * dx + dx * dy + dy * dy
        parts = 2 if math.isclose(length_squared, 4, abs_tol=1e-9) else 1
        for part in range(parts):
            edge_start = (
                start[0] + dx * part // parts,
                start[1] + dy * part // parts,
            )
            edge_end = (
                start[0] + dx * (part + 1) // parts,
                start[1] + dy * (part + 1) // parts,
            )
            edge_dx = edge_end[0] - edge_start[0]
            edge_dy = edge_end[1] - edge_start[1]
            edge_length_squared = (
                edge_dx * edge_dx + edge_dx * edge_dy + edge_dy * edge_dy
            )
            factor = ratio / math.sqrt(3) if math.isclose(edge_length_squared, 3) else 1.0
            vector = (
                (edge_dx + edge_dy / 2) * factor,
                edge_dy * math.sqrt(3) / 2 * factor,
            )
            next_x = x + vector[0]
            next_y = y + vector[1]
            edges.append((edge_start, edge_end, (x, y), (next_x, next_y)))
            points.append((next_x, next_y))
            x, y = next_x, next_y
    if math.hypot(x, y) > 1e-7:
        raise ValueError("a proporção não fecha o contorno do tile")
    return points[:-1], edges


def grow_tiling_patch(
    count,
    ratio,
    sheet_width=None,
    sheet_height=None,
    progress_interval=2.0,
    progress_scale=1.0,
):
    started_at = time.monotonic()
    last_report_at = started_at
    candidates_checked = 0
    neighbours = legal_neighbour_transforms()
    target_seed = min(count, len(SURROUNDABLE_SEED)) if count is not None else len(SURROUNDABLE_SEED)
    transforms = []
    occupied = set()
    placed = {}
    directed_edges = {}

    def add_tile(transform, require_meta_check):
        nonlocal occupied
        cells = transformed_hat_cells(transform)
        if cells & occupied:
            return False
        local_points, edges = tile_boundary(transform, ratio)
        offsets = []
        shared_edges = 0
        for start, end, local_start, local_end in edges:
            existing = directed_edges.get((end, start))
            if existing is not None:
                offsets.extend((
                    (existing[1][0] - local_start[0], existing[1][1] - local_start[1]),
                    (existing[0][0] - local_end[0], existing[0][1] - local_end[1]),
                ))
                shared_edges += 1
                continue
            existing = directed_edges.get((start, end))
            if existing is not None:
                offsets.extend((
                    (existing[0][0] - local_start[0], existing[0][1] - local_start[1]),
                    (existing[1][0] - local_end[0], existing[1][1] - local_end[1]),
                ))
                shared_edges += 1
        if transform == IDENTITY and not transforms:
            offset = (0.0, 0.0)
        elif not offsets:
            return False
        else:
            offset = offsets[0]
            if any(
                math.hypot(point[0] - offset[0], point[1] - offset[1]) > 1e-6
                for point in offsets[1:]
            ):
                return False

        if require_meta_check:
            is_valid, _ = complete_metatile_checks((*transforms, transform), transform)
            if not is_valid:
                return False

        combined = occupied | cells
        if occupied and not is_simply_connected(combined):
            return False

        transforms.append(transform)
        occupied = combined
        placed[transform] = (offset, local_points)
        for start, end, local_start, local_end in edges:
            directed_edges[(start, end)] = (
                (local_start[0] + offset[0], local_start[1] + offset[1]),
                (local_end[0] + offset[0], local_end[1] + offset[1]),
            )
        return True

    for transform in SURROUNDABLE_SEED[:target_seed]:
        if not add_tile(transform, require_meta_check=False):
            raise ValueError("a semente oficial de metatile não formou um patch conexo")

    def patch_fits_sheet():
        points = [
            (x + offset[0], y + offset[1])
            for offset, local_points in placed.values()
            for x, y in local_points
        ]
        patch_width = max(x for x, _ in points) - min(x for x, _ in points)
        patch_height = max(y for _, y in points) - min(y for _, y in points)
        return (
            patch_width <= sheet_width and patch_height <= sheet_height
        ) or (
            patch_width <= sheet_height and patch_height <= sheet_width
        )

    if sheet_width is not None and not patch_fits_sheet():
        seed_size = len(transforms)
        while seed_size > 1:
            seed_size -= 1
            transforms.clear()
            occupied.clear()
            placed.clear()
            directed_edges.clear()
            for transform in SURROUNDABLE_SEED[:seed_size]:
                if not add_tile(transform, require_meta_check=False):
                    raise ValueError("prefixo da semente oficial não formou patch conexo")
            if patch_fits_sheet():
                break
        if not patch_fits_sheet():
            raise ValueError("a peça não cabe na chapa com a margem informada")

    frontier = {
        compose_transforms(transform, neighbour)
        for transform in transforms
        for neighbour in neighbours
        if compose_transforms(transform, neighbour) not in placed
    }
    min_x = min(x + offset[0] for offset, points in placed.values() for x, _ in points)
    max_x = max(x + offset[0] for offset, points in placed.values() for x, _ in points)
    min_y = min(y + offset[1] for offset, points in placed.values() for _, y in points)
    max_y = max(y + offset[1] for offset, points in placed.values() for _, y in points)

    def report_progress(stage, force=False, bounds=None):
        nonlocal last_report_at
        now = time.monotonic()
        if not force and now - last_report_at < progress_interval:
            return
        last_report_at = now
        if bounds is None:
            width = max_x - min_x
            height = max_y - min_y
        else:
            width = bounds[1] - bounds[0]
            height = bounds[3] - bounds[2]
        target = str(count) if count is not None else "chapa"
        print(
            f"[progresso] {len(transforms)}/{target} peças; "
            f"{candidates_checked} candidatos; fronteira {len(frontier)}; "
            f"envelope {width * progress_scale:.0f} x "
            f"{height * progress_scale:.0f} mm; "
            f"{now - started_at:.1f}s; {stage}",
            file=sys.stderr,
            flush=True,
        )

    report_progress("iniciando expansão", force=True)

    while count is None or len(transforms) < count:
        candidates = []
        for candidate in frontier.copy():
            candidates_checked += 1
            report_progress("avaliando fronteira")
            cells = transformed_hat_cells(candidate)
            if cells & occupied:
                frontier.discard(candidate)
                continue
            local_points, edges = tile_boundary(candidate, ratio)
            offsets = []
            shared = []
            for start, end, local_start, local_end in edges:
                existing = directed_edges.get((end, start))
                if existing is not None:
                    offsets.extend((
                        (existing[1][0] - local_start[0], existing[1][1] - local_start[1]),
                        (existing[0][0] - local_end[0], existing[0][1] - local_end[1]),
                    ))
                    shared.append((start, end))
                    continue
                existing = directed_edges.get((start, end))
                if existing is None:
                    continue
                offsets.extend((
                    (existing[0][0] - local_start[0], existing[0][1] - local_start[1]),
                    (existing[1][0] - local_end[0], existing[1][1] - local_end[1]),
                ))
                shared.append((start, end))
            if not shared:
                continue
            offset = offsets[0]
            if any(
                math.hypot(point[0] - offset[0], point[1] - offset[1]) > 1e-6
                for point in offsets[1:]
            ):
                frontier.discard(candidate)
                continue

            new_min_x = min(min_x, *(x + offset[0] for x, _ in local_points))
            new_max_x = max(max_x, *(x + offset[0] for x, _ in local_points))
            new_min_y = min(min_y, *(y + offset[1] for _, y in local_points))
            new_max_y = max(max_y, *(y + offset[1] for _, y in local_points))
            width = new_max_x - new_min_x
            height = new_max_y - new_min_y
            if sheet_width is not None:
                fits = (
                    (width <= sheet_width and height <= sheet_height)
                    or (width <= sheet_height and height <= sheet_width)
                )
                if not fits:
                    frontier.discard(candidate)
                    continue
                compactness = min(
                    max(width / sheet_width, height / sheet_height),
                    max(width / sheet_height, height / sheet_width),
                )
                key = (
                    compactness,
                    -(width * height),
                    abs(width / sheet_width - height / sheet_height),
                    -len(shared),
                    candidate,
                )
            else:
                key = (
                    max(width, height), width * height, abs(width - height),
                    -len(shared), candidate,
                )
            candidates.append((
                key, candidate, cells, offset, local_points, edges,
                (new_min_x, new_max_x, new_min_y, new_max_y),
            ))

        candidates.sort(key=lambda item: item[0])
        best = None
        for item in candidates:
            _, candidate, cells, offset, local_points, edges, bounds = item
            candidate_patch = (*transforms, candidate)
            valid, _ = complete_metatile_checks(candidate_patch, candidate)
            report_progress("checando metatiles", bounds=bounds)
            if not valid or not is_simply_connected(occupied | cells):
                continue
            best = item
            break

        if best is None:
            if count is None:
                break
            raise ValueError(
                f"não foi possível ampliar o patch validado; geradas {len(transforms)} peças"
            )

        _, candidate, _, offset, _, _, bounds = best
        frontier.discard(candidate)
        if not add_tile(candidate, require_meta_check=False):
            raise ValueError("falha ao registrar tile após validar metatiles")
        min_x, max_x, min_y, max_y = bounds
        frontier.update(
            compose_transforms(candidate, neighbour)
            for neighbour in neighbours
            if compose_transforms(candidate, neighbour) not in placed
        )
        report_progress("tile aceito", bounds=bounds)

    unique_edges = {}
    all_points = []
    for offset, points in placed.values():
        all_points.extend((x + offset[0], y + offset[1]) for x, y in points)
    min_x = min(x for x, _ in all_points)
    min_y = min(y for _, y in all_points)
    max_x = max(x for x, _ in all_points)
    max_y = max(y for _, y in all_points)
    for transform, (offset, _) in placed.items():
        _, edges = tile_boundary(transform, ratio)
        for _, _, local_start, local_end in edges:
            start = (round(local_start[0] + offset[0] - min_x, 6),
                     round(max_y - local_start[1] - offset[1], 6))
            end = (round(local_end[0] + offset[0] - min_x, 6),
                   round(max_y - local_end[1] - offset[1], 6))
            edge_key = tuple(sorted((start, end)))
            unique_edges[edge_key] = (start, end)
    report_progress("concluído", force=True, bounds=(min_x, max_x, min_y, max_y))
    return (
        list(unique_edges.values()),
        max_x - min_x,
        max_y - min_y,
        len(transforms),
        tuple(transforms),
        tuple((transform, placement[0]) for transform, placement in placed.items()),
    )


def main():
    args = parse_args()
    sheet_width = args.sheet_cm[0] * 10 if args.sheet_cm else None
    sheet_height = args.sheet_cm[1] * 10 if args.sheet_cm else None
    available_width = sheet_width - 2 * args.margin_mm if sheet_width else None
    available_height = sheet_height - 2 * args.margin_mm if sheet_height else None
    if available_width is not None and min(available_width, available_height) <= 0:
        raise SystemExit("Erro: a margem é maior que a chapa")

    try:
        grid = load_grid(args.grid_json) if args.grid_json else HAT_GRID
        ratio = args.ratio or DEFAULT_RATIOS.get(args.tile, 1.0)
        if args.layout == "tiling":
            local_points, _ = tile_boundary(IDENTITY, ratio)
        elif args.tile == "spectre":
            local_points = SPECTRE_OUTLINE
        else:
            local_points = points_from_segments(grid_edges(grid, ratio))
    except ValueError as error:
        raise SystemExit(f"Erro: {error}") from error

    max_diameter = diameter(local_points)
    scale_mm = (
        args.module_mm
        if args.module_mm is not None
        else (args.size_cm if args.size_cm is not None else 5.0) * 10 / max_diameter
    )
    actual_diameter = max_diameter * scale_mm
    tile_area = polygon_area(local_points) * scale_mm * scale_mm
    try:
        if args.layout == "tiling":
            max_width = available_width / scale_mm if available_width else None
            max_height = available_height / scale_mm if available_height else None
            (
                cut_edges,
                patch_width,
                patch_height,
                count,
                transforms,
                placements,
            ) = grow_tiling_patch(
                args.count,
                ratio,
                max_width,
                max_height,
                args.progress_interval,
                scale_mm,
            )
            patch_width *= scale_mm
            patch_height *= scale_mm
            rotate_patch = False
            if sheet_width is None:
                width, height = patch_width, patch_height
                offset_x = offset_y = 0.0
            else:
                rotate_patch = (
                    max(patch_height / available_width, patch_width / available_height)
                    < max(patch_width / available_width, patch_height / available_height)
                )
                if rotate_patch:
                    cut_edges = [
                        ((patch_height - start[1], start[0]),
                         (patch_height - end[1], end[0]))
                        for start, end in cut_edges
                    ]
                    patch_width, patch_height = patch_height, patch_width
                offset_x = args.margin_mm + (available_width - patch_width) / 2
                offset_y = args.margin_mm + (available_height - patch_height) / 2
                width, height = sheet_width, sheet_height
            paths = [
                f'  <path d="M {start[0] * scale_mm + offset_x:.3f} '
                f'{start[1] * scale_mm + offset_y:.3f} L '
                f'{end[0] * scale_mm + offset_x:.3f} '
                f'{end[1] * scale_mm + offset_y:.3f}" />'
                for start, end in cut_edges
            ]
            metadata = {
                "schema": "hat-metatile-patch-v1",
                "source": "arXiv:2303.10798 anc/validate/2patches.txt",
                "tile": args.tile,
                "ratio": ratio,
                "count": count,
                "transforms": transforms,
                "placements": [
                    {"transform": transform, "offset": offset}
                    for transform, offset in placements
                ],
                "scale_mm": scale_mm,
                "rotate_patch": rotate_patch,
                "svg_offset_mm": [offset_x, offset_y],
            }
        else:
            points = [(x * scale_mm, y * scale_mm) for x, y in local_points]
            min_x = min(x for x, _ in points)
            min_y = min(y for _, y in points)
            max_x = max(x for x, _ in points)
            max_y = max(y for _, y in points)
            tile_width = max_x - min_x
            tile_height = max_y - min_y
            rotate_tiles = False
            if sheet_width is not None and args.count is None:
                orientations = []
                for rotated, item_width, item_height in (
                    (False, tile_width, tile_height),
                    (True, tile_height, tile_width),
                ):
                    columns_fit = math.floor(
                        (available_width + args.gap_mm)
                        / (item_width + args.gap_mm)
                    )
                    rows_fit = math.floor(
                        (available_height + args.gap_mm)
                        / (item_height + args.gap_mm)
                    )
                    orientations.append((
                        columns_fit * rows_fit,
                        rotated,
                        columns_fit,
                        rows_fit,
                        item_width,
                        item_height,
                    ))
                count, rotate_tiles, columns, rows, tile_width, tile_height = max(
                    orientations
                )
                if count == 0:
                    raise ValueError("nenhuma peça cabe na chapa com a margem informada")
            else:
                count = args.count
                columns = min(args.columns, count)
                rows = math.ceil(count / columns)
            patch_width = columns * tile_width + (columns - 1) * args.gap_mm
            patch_height = rows * tile_height + (rows - 1) * args.gap_mm
            width = sheet_width if sheet_width is not None else patch_width
            height = sheet_height if sheet_height is not None else patch_height
            offset_x = (
                args.margin_mm + (available_width - patch_width) / 2
                if sheet_width is not None else 0.0
            )
            offset_y = (
                args.margin_mm + (available_height - patch_height) / 2
                if sheet_height is not None else 0.0
            )

            paths = []
            metadata = None
            for index in range(count):
                column = index % columns
                row = index // columns
                offset_x = column * (tile_width + args.gap_mm)
                offset_y = row * (tile_height + args.gap_mm)
                vertices = [
                    (
                        (y - min_y if rotate_tiles else x - min_x)
                        + column * (tile_width + args.gap_mm),
                        (max_x - x if rotate_tiles else max_y - y)
                        + row * (tile_height + args.gap_mm),
                    )
                    for x, y in points
                ]
                if sheet_width is not None:
                    vertices = [
                        (x + args.margin_mm + (available_width - patch_width) / 2,
                         y + args.margin_mm + (available_height - patch_height) / 2)
                        for x, y in vertices
                    ]
                path_data = " ".join(
                    f"{'M' if vertex == 0 else 'L'} {x:.3f} {y:.3f}"
                    for vertex, (x, y) in enumerate(vertices)
                ) + " Z"
                paths.append(f'  <path d="{path_data}" />')
    except ValueError as error:
        raise SystemExit(f"Erro ao organizar o patch: {error}") from error

    metadata_element = (
        f"  <metadata>{json.dumps(metadata, separators=(',', ':'))}</metadata>"
        if metadata is not None else ""
    )
    svg = "\n".join(
        (
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width:.3f}mm" height="{height:.3f}mm" '
            f'viewBox="0 0 {width:.3f} {height:.3f}">',
            metadata_element,
            '  <g fill="none" stroke="#ff0000" stroke-width="0.1">',
            *paths,
            "  </g>",
            "</svg>",
            "",
        )
    )
    Path(args.output).write_text(svg, encoding="utf-8")
    patch_area = count * tile_area
    patch_compactness = 100 * patch_area / (patch_width * patch_height)
    sheet_utilization = (
        100 * patch_area / (sheet_width * sheet_height)
        if sheet_width is not None else patch_compactness
    )
    print(
        f"SVG gerado: {args.output} ({args.tile}, {count} peça(s), "
        f"diâmetro {actual_diameter:.2f} mm, placa {width:.1f} x {height:.1f} mm, "
        f"compactação {patch_compactness:.1f}%, aproveitamento da chapa "
        f"{sheet_utilization:.1f}%, {len(paths)} traços de corte)"
    )


if __name__ == "__main__":
    main()