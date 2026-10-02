#!/usr/bin/env python3
"""
Azulejo Aperiódico para corte a laser.

Layout:
- Moldura externa com espessura configurável
- Borda inferior MENOR: espessura = ln(1.5) × espessura_borda
- Quadrado interno vazio (área de jogo)
- Título "AZULEJO APERIÓDICO" auto-ajustado à largura disponível
- Metatiles H, T, P, F empilhados verticalmente nas laterais esquerda/direita
- Setas de orientação em H, T, P (F não tem seta — parte do triskelion)

Uso:
    python tabuleiro.py --tamanho-interno-cm 20 \\
                        --espessura-borda-cm 3 \\
                        --multiplicador-perimetro 0.8 \\
                        --arquivo-saida Tabuleiro.svg
"""

import argparse
import math
from pathlib import Path

# ==============================================================================
# GEOMETRIA BASE DOS METATILES
# ==============================================================================
SQRT3 = math.sqrt(3)
HR3 = SQRT3 / 2


def hexPt(x, y):
    return (x + 0.5 * y, HR3 * y)


HAT_OUTLINE = [
    hexPt(0, 0), hexPt(-1, -1), hexPt(0, -2), hexPt(2, -2),
    hexPt(2, -1), hexPt(4, -2), hexPt(5, -1), hexPt(4, 0),
    hexPt(3, 0), hexPt(2, 2), hexPt(0, 3), hexPt(0, 2),
    hexPt(-1, 2)
]
H_OUTLINE = [(0, 0), (4, 0), (4.5, HR3), (2.5, 5 * HR3), (1.5, 5 * HR3), (-0.5, HR3)]
T_OUTLINE = [(0, 0), (3, 0), (1.5, 3 * HR3)]
P_OUTLINE = [(0, 0), (4, 0), (3, 2 * HR3), (-1, 2 * HR3)]
F_OUTLINE = [(0, 0), (3, 0), (3.5, HR3), (3, 2 * HR3), (-1, 2 * HR3)]


# ==============================================================================
# SETA SIMPLIFICADA DE 10 PONTOS (H, T, P têm seta; F não tem)
# ==============================================================================
def make_arrow_10pts(center, direction, size):
    """Seta clássica (haste + ponta), 10 vértices."""
    cx, cy = center
    dx, dy = direction
    px, py = -dy, dx

    shaft_len = size * 0.55
    head_len = size * 0.45
    shaft_half = size * 0.06
    head_half = size * 0.20

    tail_x = cx - dx * shaft_len * 0.5
    tail_y = cy - dy * shaft_len * 0.5
    head_base_x = cx + dx * shaft_len * 0.5
    head_base_y = cy + dy * shaft_len * 0.5
    tip_x = cx + dx * (shaft_len * 0.5 + head_len)
    tip_y = cy + dy * (shaft_len * 0.5 + head_len)

    p1 = (tail_x + px * shaft_half, tail_y + py * shaft_half)
    p2 = (head_base_x + px * shaft_half, head_base_y + py * shaft_half)
    p3 = (head_base_x + px * head_half, head_base_y + py * head_half)
    p4 = (head_base_x + px * head_half * 0.5, head_base_y + py * head_half * 0.5)
    p5 = (tip_x, tip_y)
    p6 = (head_base_x - px * head_half * 0.5, head_base_y - py * head_half * 0.5)
    p7 = (head_base_x - px * head_half, head_base_y - py * head_half)
    p8 = (head_base_x - px * shaft_half, head_base_y - py * shaft_half)
    p9 = (tail_x - px * shaft_half, tail_y - py * shaft_half)
    p10 = (tail_x - px * shaft_half * 0.3, tail_y - py * shaft_half * 0.3)

    return [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10]


# Aresta alvo para cada metatile (F não tem seta — triskelion)
TARGET_EDGE = {
    'H': (0, 1),
    'T': (0, 1),
    'P': (0, 1),
}


# ==============================================================================
# UTILITÁRIOS GEOMÉTRICOS
# ==============================================================================
def polygon_centroid(pts):
    return (sum(p[0] for p in pts) / len(pts),
            sum(p[1] for p in pts) / len(pts))


def scale_to_max_dim(shape, target_max_dim):
    """Escala a forma para que sua MAIOR dimensão (bounding box) = target_max_dim."""
    xs = [p[0] for p in shape]
    ys = [p[1] for p in shape]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    max_dim = max(w, h)
    if max_dim < 1e-9:
        return list(shape), 1.0
    scale = target_max_dim / max_dim
    cx, cy = polygon_centroid(shape)
    pts = [((x - cx) * scale, (y - cy) * scale) for x, y in shape]
    return pts, scale


def translate(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def rotate(pts, angle_rad):
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def compute_arrow_polygon(shape_pts, label, target_edge, arrow_size_mm):
    """Calcula o polígono da seta apontando para a aresta alvo."""
    if label not in target_edge:
        return None
    iA, iB = target_edge[label]
    n = len(shape_pts)
    if iA >= n or iB >= n:
        return None

    cx, cy = polygon_centroid(shape_pts)
    A = shape_pts[iA]
    B = shape_pts[iB]
    mid = ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2)

    dx = mid[0] - cx
    dy = mid[1] - cy
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return None
    dx /= L
    dy /= L

    # 15% do caminho do centroide até a aresta alvo
    px = cx + dx * L * 0.15
    py = cy + dy * L * 0.15
    return make_arrow_10pts((px, py), (dx, dy), arrow_size_mm)


# ==============================================================================
# GERAÇÃO DO AZULEJO
# ==============================================================================
def gerar_azulejo_aperiodico(
    tamanho_interno_cm=20.0,
    espessura_borda_cm=3.0,
    multiplicador_perimetro=2.0,
    arquivo_saida="azulejo_aperiodico.svg",
):
    inner_mm = tamanho_interno_cm * 10.0
    border_mm = espessura_borda_cm * 10.0

    # Borda INFERIOR menor: ln(1.5) × espessura padrão
    bottom_ratio = math.log(1.5)          # ≈ 0.405465
    bottom_mm = bottom_ratio * border_mm

    # Dimensões totais (chapa retangular pois a borda inferior é menor)
    total_width = inner_mm + 2 * border_mm
    total_height = inner_mm + border_mm + bottom_mm

    # Coordenadas do quadrado interno
    x_min = border_mm
    y_min = border_mm
    x_max = x_min + inner_mm
    y_max = y_min + inner_mm
    center_x = total_width / 2

    # ------------------------------------------------------------------
    # CÁLCULO DO TÍTULO — auto-ajustado à largura disponível
    # ------------------------------------------------------------------
    title_max_width_mm = total_width * 0.80   # 80% da largura, com margem

    title_main = "AZULEJO APERIÓDICO"
    title_subtitle = "EINSTEIN MONOTILE · HAT POLYKITE"

    n_chars_main = len(title_main)
    n_chars_subtitle = len(title_subtitle)

    # Cada letra ocupa ~ font_size * 0.62 de largura + letter_spacing (0.5 * font_size)
    LETRA_FATOR = 1.12
    font_main_mm = title_max_width_mm / (n_chars_main * LETRA_FATOR)
    font_main_mm = max(6.0, min(font_main_mm, border_mm * 0.65))

    letter_spacing_main = font_main_mm * 0.5
    font_sub_mm = font_main_mm * 0.40
    letter_spacing_sub = font_sub_mm * 0.6

    # Posições verticais dentro da borda superior
    y_line_top = border_mm * 0.18
    y_main = border_mm * 0.50
    y_sub = border_mm * 0.78
    y_line_bottom = border_mm * 0.92

    line_half = title_max_width_mm * 0.45

    print(f"  Título: {title_main}")
    print(f"    Fonte principal: {font_main_mm:.2f} mm  (letter-spacing {letter_spacing_main:.2f} mm)")
    print(f"    Fonte subtítulo: {font_sub_mm:.2f} mm")
    print(f"    Largura útil:    {title_max_width_mm:.1f} mm")

    # ------------------------------------------------------------------
    # Posições dos metatiles nas LATERAIS (esquerda e direita)
    # ------------------------------------------------------------------
    step_y = inner_mm / 4.0
    y_positions = [y_min + step_y * (i + 0.5) for i in range(4)]
    labels = ['H', 'T', 'P', 'F']

    placements = []
    # Lateral esquerda (rot 90°)
    for i, label in enumerate(labels):
        placements.append((label, x_min / 2.0, y_positions[i], 90))
    # Lateral direita (rot -90°)
    for i, label in enumerate(labels):
        placements.append((label, x_max + border_mm / 2.0, y_positions[i], -90))

    target_max_dim = multiplicador_perimetro * border_mm
    arrow_size = max(2.0, min(target_max_dim * 0.1, 6.0))

    shapes = {
        'H': H_OUTLINE,
        'T': T_OUTLINE,
        'P': P_OUTLINE,
        'F': F_OUTLINE,
    }

    piece_svgs = []
    arrow_svgs = []

    for label, cx, cy, angle_deg in placements:
        shape = shapes[label]
        pts, _ = scale_to_max_dim(shape, target_max_dim)
        pts = rotate(pts, math.radians(angle_deg))
        pts = translate(pts, cx, cy)

        pts_str = " ".join(f"{x:.3f},{y:.3f}" for x, y in pts)
        piece_svgs.append(
            f'    <polygon points="{pts_str}" class="gravura-peca" />'
        )

        arrow_pts = compute_arrow_polygon(pts, label, TARGET_EDGE, arrow_size)
        if arrow_pts:
            arrow_str = " ".join(f"{x:.3f},{y:.3f}" for x, y in arrow_pts)
            arrow_svgs.append(
                f'    <polygon points="{arrow_str}" class="gravura-seta" />'
            )

    # ==================================================================
    # SVG FINAL
    # ==================================================================
    svg_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{total_width}mm" height="{total_height}mm"
     viewBox="0 0 {total_width} {total_height}">

  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&amp;display=swap');

      .corte-externo {{ fill: none; stroke: #ff0000; stroke-width: 0.5; }}
      .corte-interno {{ fill: none; stroke: #0000ff; stroke-width: 0.3; }}
      .gravura-peca  {{ fill: none; stroke: #000000; stroke-width: 0.25; }}
      .gravura-seta  {{ fill: none; stroke: #00aa00; stroke-width: 0.2; }}

      /* Título calculado em mm para caber sempre na área disponível */
      .titulo-principal {{
        font-family: 'Space Grotesk', 'Inter', 'Helvetica Neue', Arial, sans-serif;
        font-weight: 700;
        font-size: {font_main_mm:.3f}px;
        letter-spacing: {letter_spacing_main:.3f}px;
        fill: #111111;
        text-anchor: middle;
        dominant-baseline: middle;
      }}
      .titulo-secundario {{
        font-family: 'Space Grotesk', 'Inter', 'Helvetica Neue', Arial, sans-serif;
        font-weight: 400;
        font-size: {font_sub_mm:.3f}px;
        letter-spacing: {letter_spacing_sub:.3f}px;
        fill: #555555;
        text-anchor: middle;
        dominant-baseline: middle;
      }}
      .titulo-linha {{
        stroke: #111111;
        stroke-width: 0.4;
      }}
    </style>
  </defs>

  <!-- 1. Contorno externo da chapa (corte) -->
  <rect x="0" y="0" width="{total_width}" height="{total_height}"
        class="corte-externo" />

  <!-- 2. Quadrado interno (referência de corte) -->
  <rect x="{x_min}" y="{y_min}" width="{inner_mm}" height="{inner_mm}"
        class="corte-interno" />

  <!-- 3. Bloco de Título (auto-ajustado à largura disponível) -->
  <g id="titulo-bloco">
    <!-- Linha decorativa superior -->
    <line x1="{center_x - line_half:.2f}" y1="{y_line_top:.2f}"
          x2="{center_x + line_half:.2f}" y2="{y_line_top:.2f}"
          class="titulo-linha" />

    <!-- Título principal (forçado à largura via textLength) -->
    <text x="{center_x:.2f}" y="{y_main:.2f}"
          class="titulo-principal"
          textLength="{title_max_width_mm * 0.95:.2f}"
          lengthAdjust="spacingAndGlyphs">{title_main}</text>

    <!-- Subtítulo -->
    <text x="{center_x:.2f}" y="{y_sub:.2f}"
          class="titulo-secundario"
          textLength="{title_max_width_mm * 0.75:.2f}"
          lengthAdjust="spacingAndGlyphs">{title_subtitle}</text>

    <!-- Linha decorativa inferior -->
    <line x1="{center_x - line_half:.2f}" y1="{y_line_bottom:.2f}"
          x2="{center_x + line_half:.2f}" y2="{y_line_bottom:.2f}"
          class="titulo-linha" />
  </g>

  <!-- 4. Metatiles H, T, P, F nas laterais -->
  <g id="metatiles_gravura">
{chr(10).join(piece_svgs)}
  </g>

  <!-- 5. Setas de orientação (H, T, P) -->
  <g id="setas_gravura">
{chr(10).join(arrow_svgs)}
  </g>

</svg>
"""

    caminho = Path(arquivo_saida)
    caminho.write_text(svg_content, encoding="utf-8")

    print(f"Arquivo gerado: {caminho.resolve()}")
    print(f"  Chapa total:        {total_width:.1f} x {total_height:.1f} mm")
    print(f"  Quadrado interno:   {inner_mm:.0f} x {inner_mm:.0f} mm")
    print(f"  Borda topo/laterais:{border_mm:.2f} mm")
    print(f"  Borda inferior:     {bottom_mm:.2f} mm (ln(1.5) × {border_mm:.1f})")
    print(f"  Dimensão máx peça:  {target_max_dim:.2f} mm")
    print(f"  Seta:               {arrow_size:.2f} mm")
    print("  Posições dos metatiles:")
    for i, label in enumerate(labels):
        print(f"    {label}: esq=({x_min / 2:.0f}, {y_positions[i]:.0f})  "
              f"dir=({x_max + border_mm / 2:.0f}, {y_positions[i]:.0f})")


# ==============================================================================
# INTERFACE DE LINHA DE COMANDO
# ==============================================================================
def parse_args():
    parser = argparse.ArgumentParser(
        description="Gera um SVG do Azulejo Aperiódico para corte a laser.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--tamanho-interno-cm",
        type=float,
        default=20.0,
        metavar="CM",
        help="Lado do quadrado interno (área de jogo) em centímetros.",
    )
    parser.add_argument(
        "--espessura-borda-cm",
        type=float,
        default=3.0,
        metavar="CM",
        help="Espessura da moldura (topo e laterais) em centímetros. "
             "A borda inferior recebe ln(1.5) × este valor.",
    )
    parser.add_argument(
        "--multiplicador-perimetro",
        type=float,
        default=2.0,
        metavar="FATOR",
        help="Fator multiplicador da maior dimensão de cada metatile, "
             "relativo à espessura da borda. Ex.: 2.0 = peça com o dobro da borda.",
    )
    parser.add_argument(
        "--arquivo-saida",
        type=str,
        default="tabuleiro.svg",
        metavar="ARQUIVO",
        help="Nome do arquivo SVG de saída.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print("=" * 60)
    print("AZULEJO APERIÓDICO — Gerador para corte a laser")
    print("=" * 60)
    print(f"  Tamanho interno:        {args.tamanho_interno_cm} cm")
    print(f"  Espessura da borda:     {args.espessura_borda_cm} cm")
    print(f"  Multiplicador perímetro:{args.multiplicador_perimetro}")
    print(f"  Arquivo de saída:       {args.arquivo_saida}")
    print()

    gerar_azulejo_aperiodico(
        tamanho_interno_cm=args.tamanho_interno_cm,
        espessura_borda_cm=args.espessura_borda_cm,
        multiplicador_perimetro=args.multiplicador_perimetro,
        arquivo_saida=args.arquivo_saida,
    )


if __name__ == "__main__":
    main()