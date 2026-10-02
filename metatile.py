#!/usr/bin/env python3
"""Gera SVG para corte a laser com metatiles (H,T,P,F) de nível 1.

- Decompõe todos os níveis (0..max) em metatiles de nível 1.
- Filtra apenas peças 100% dentro da área útil (guilhotina: peças inteiras ou descartadas).
- Deduplica arestas de corte.
- Setas simplificadas em 10 pontos, clipadas com Cohen-Sutherland (segmentos de reta).
"""

import argparse
import math
from pathlib import Path

SQRT3 = math.sqrt(3)
HR3 = SQRT3 / 2

# ==============================================================================
# GEOMETRIA BASE
# ==============================================================================
def hexPt(x, y):
    return (x + 0.5 * y, HR3 * y)

HAT_OUTLINE = [
    hexPt(0, 0), hexPt(-1,-1), hexPt(0,-2), hexPt(2,-2),
    hexPt(2,-1), hexPt(4,-2), hexPt(5,-1), hexPt(4, 0),
    hexPt(3, 0), hexPt(2, 2), hexPt(0, 3), hexPt(0, 2),
    hexPt(-1, 2)
]
H_OUTLINE = [ (0, 0), (4, 0), (4.5, HR3), (2.5, 5 * HR3), (1.5, 5 * HR3), (-0.5, HR3) ]
T_OUTLINE = [ (0, 0), (3, 0), (1.5, 3 * HR3) ]
P_OUTLINE = [ (0, 0), (4, 0), (3, 2 * HR3), (-1, 2 * HR3) ]
F_OUTLINE = [ (0, 0), (3, 0), (3.5, HR3), (3, 2 * HR3), (-1, 2 * HR3) ]

# ==============================================================================
# ÁLGEBRA DE MATRIZES AFINS
# ==============================================================================
def mat_mul(A, B):
    a1, b1, c1, d1, e1, f1 = A
    a2, b2, c2, d2, e2, f2 = B
    return (
        a1*a2 + b1*d2, a1*b2 + b1*e2, a1*c2 + b1*f2 + c1,
        d1*a2 + e1*d2, d1*b2 + e1*e2, d1*c2 + e1*f2 + f1
    )

def mat_inv(T):
    a, b, c, d, e, f = T
    det = a*e - b*d
    if abs(det) < 1e-12:
        raise ValueError(f"Matriz singular: det={det}")
    return (e/det, -b/det, (b*f - e*c)/det, -d/det, a/det, (d*c - a*f)/det)

def transform_point(T, p):
    a, b, c, d, e, f = T
    return (a*p[0] + b*p[1] + c, d*p[0] + e*p[1] + f)

def match_seg(p, q):
    return (q[0]-p[0], p[1]-q[1], p[0], q[1]-p[1], q[0]-p[0], p[1])

def match_two(p1, q1, p2, q2):
    return mat_mul(match_seg(p2, q2), mat_inv(match_seg(p1, q1)))

# ==============================================================================
# CLASSES DO SISTEMA-L
# ==============================================================================
class HatLeaf:
    def __init__(self, label, reflected=False):
        self.label = label
        self.reflected = reflected

class MetaTile:
    def __init__(self, shape, label=""):
        self.shape = shape
        self.children = []
        self.label = label
    def add_child(self, transform, node):
        self.children.append((transform, node))

def recentre(meta):
    if not meta.shape:
        return
    cx = sum(p[0] for p in meta.shape) / len(meta.shape)
    cy = sum(p[1] for p in meta.shape) / len(meta.shape)
    meta.shape = [(p[0]-cx, p[1]-cy) for p in meta.shape]
    T_trans = (1, 0, -cx, 0, 1, -cy)
    meta.children = [(mat_mul(T_trans, T), node) for T, node in meta.children]

# ==============================================================================
# METATILES NÍVEL 0 (BASE)
# ==============================================================================
def build_H_init():
    meta = MetaTile(H_OUTLINE, "H")
    meta.add_child(match_two(HAT_OUTLINE[5], HAT_OUTLINE[7], H_OUTLINE[5], H_OUTLINE[0]), HatLeaf("H"))
    meta.add_child(match_two(HAT_OUTLINE[9], HAT_OUTLINE[11], H_OUTLINE[1], H_OUTLINE[2]), HatLeaf("H"))
    meta.add_child(match_two(HAT_OUTLINE[5], HAT_OUTLINE[7], H_OUTLINE[3], H_OUTLINE[4]), HatLeaf("H"))
    T1 = (-0.5, -HR3, 0, HR3, -0.5, 0)
    T2 = (0.5, 0, 0, 0, -0.5, 0)
    T3 = (1, 0, 2.5, 0, 1, HR3)
    meta.add_child(mat_mul(T3, mat_mul(T1, T2)), HatLeaf("H1", reflected=True))
    recentre(meta)
    return meta

def build_T_init():
    meta = MetaTile(T_OUTLINE, "T")
    meta.add_child((0.5, 0, 0.5, 0, 0.5, HR3), HatLeaf("T"))
    recentre(meta)
    return meta

def build_P_init():
    meta = MetaTile(P_OUTLINE, "P")
    meta.add_child((0.5, 0, 1.5, 0, 0.5, HR3), HatLeaf("P"))
    T1 = (0.5, HR3, 0, -HR3, 0.5, 0)
    T2 = (0.5, 0, 0, 0, 0.5, 0)
    T3 = (1, 0, 0, 0, 1, 2 * HR3)
    meta.add_child(mat_mul(T3, mat_mul(T1, T2)), HatLeaf("P"))
    recentre(meta)
    return meta

def build_F_init():
    meta = MetaTile(F_OUTLINE, "F")
    meta.add_child((0.5, 0, 1.5, 0, 0.5, HR3), HatLeaf("F"))
    T1 = (0.5, HR3, 0, -HR3, 0.5, 0)
    T2 = (0.5, 0, 0, 0, 0.5, 0)
    T3 = (1, 0, 0, 0, 1, 2 * HR3)
    meta.add_child(mat_mul(T3, mat_mul(T1, T2)), HatLeaf("F"))
    recentre(meta)
    return meta

# ==============================================================================
# SISTEMA DE SUBSTITUIÇÃO (PATCH + METATILES)
# ==============================================================================
def construct_patch(H, T, P, F):
    rules = [
        ['H'], [0, 0, 'P', 2], [1, 0, 'H', 2], [2, 0, 'P', 2], [3, 0, 'H', 2],
        [4, 4, 'P', 2], [0, 4, 'F', 3], [2, 4, 'F', 3], [4, 1, 3, 2, 'F', 0],
        [8, 3, 'H', 0], [9, 2, 'P', 0], [10, 2, 'H', 0], [11, 4, 'P', 2],
        [12, 0, 'H', 2], [13, 0, 'F', 3], [14, 2, 'F', 1], [15, 3, 'H', 4],
        [8, 2, 'F', 1], [17, 3, 'H', 0], [18, 2, 'P', 0], [19, 2, 'H', 2],
        [20, 4, 'F', 3], [20, 0, 'P', 2], [22, 0, 'H', 2], [23, 4, 'F', 3],
        [23, 0, 'F', 3], [16, 0, 'P', 2], [9, 4, 0, 2, 'T', 2], [4, 0, 'F', 3]
    ]
    ret = MetaTile([], "patch")
    shapes = {'H': H, 'T': T, 'P': P, 'F': F}
    ident = (1, 0, 0, 0, 1, 0)

    for r in rules:
        if len(r) == 1:
            ret.add_child(ident, shapes[r[0]])
        elif len(r) == 4:
            p_idx, p_edge, c_type, c_edge = r
            poly = ret.children[p_idx][1].shape
            T_parent = ret.children[p_idx][0]
            P_pt = transform_point(T_parent, poly[(p_edge+1) % len(poly)])
            Q = transform_point(T_parent, poly[p_edge])
            nshp = shapes[c_type]
            T_child = match_two(nshp.shape[c_edge],
                                nshp.shape[(c_edge+1) % len(nshp.shape)],
                                P_pt, Q)
            ret.add_child(T_child, nshp)
        else:
            p_idx, p_edge, q_idx, q_edge, c_type, c_edge = r
            chP = ret.children[p_idx]
            chQ = ret.children[q_idx]
            P_pt = transform_point(chQ[0], chQ[1].shape[q_edge])
            Q = transform_point(chP[0], chP[1].shape[p_edge])
            nshp = shapes[c_type]
            T_child = match_two(nshp.shape[c_edge],
                                nshp.shape[(c_edge+1) % len(nshp.shape)],
                                P_pt, Q)
            ret.add_child(T_child, nshp)
    return ret

def construct_metatiles(patch):
    def eval_child(n, i):
        T_mat = patch.children[n][0]
        shape = patch.children[n][1].shape
        return transform_point(T_mat, shape[i])

    bps1 = eval_child(8, 2)
    bps2 = eval_child(21, 2)

    def rot_about(p, ang):
        c, s = math.cos(ang), math.sin(ang)
        T_rot = (c, -s, 0, s, c, 0)
        T1 = (1, 0, p[0], 0, 1, p[1])
        T2 = (1, 0, -p[0], 0, 1, -p[1])
        return mat_mul(T1, mat_mul(T_rot, T2))

    rbps = transform_point(rot_about(bps1, -2.0 * math.pi / 3.0), bps2)
    p72 = eval_child(7, 2)
    p252 = eval_child(25, 2)

    def intersect_lines(p1, q1, p2, q2):
        d = (q2[1] - p2[1]) * (q1[0] - p1[0]) - (q2[0] - p2[0]) * (q1[1] - p1[1])
        if abs(d) < 1e-12:
            raise ValueError("Linhas paralelas")
        uA = ((q2[0] - p2[0]) * (p1[1] - p2[1]) - (q2[1] - p2[1]) * (p1[0] - p2[0])) / d
        return (p1[0] + uA * (q1[0] - p1[0]), p1[1] + uA * (q1[1] - p1[1]))

    llc = intersect_lines(bps1, rbps, eval_child(6, 2), p72)
    w = (eval_child(6, 2)[0] - llc[0], eval_child(6, 2)[1] - llc[1])
    new_H_outline = [llc, bps1]

    def trot(ang):
        c, s = math.cos(ang), math.sin(ang)
        return (c, -s, 0, s, c, 0)

    w = transform_point(trot(-math.pi/3), w)
    new_H_outline.append((new_H_outline[1][0] + w[0], new_H_outline[1][1] + w[1]))
    new_H_outline.append(eval_child(14, 2))
    w = transform_point(trot(-math.pi/3), w)
    new_H_outline.append((new_H_outline[3][0] - w[0], new_H_outline[3][1] - w[1]))
    new_H_outline.append(eval_child(6, 2))

    new_H = MetaTile(new_H_outline, "H")
    for ch in [0, 9, 16, 27, 26, 6, 1, 8, 10, 15]:
        new_H.add_child(patch.children[ch][0], patch.children[ch][1])

    v = (bps1[0] - llc[0], bps1[1] - llc[1])
    new_P_outline = [p72, (p72[0] + v[0], p72[1] + v[1]), bps1, llc]
    new_P = MetaTile(new_P_outline, "P")
    for ch in [7, 2, 3, 4, 28]:
        new_P.add_child(patch.children[ch][0], patch.children[ch][1])

    v2 = (llc[0] - bps1[0], llc[1] - bps1[1])
    new_F_outline = [bps2, eval_child(24, 2), eval_child(25, 0),
                     p252, (p252[0] + v2[0], p252[1] + v2[1])]
    new_F = MetaTile(new_F_outline, "F")
    for ch in [21, 20, 22, 23, 24, 25]:
        new_F.add_child(patch.children[ch][0], patch.children[ch][1])

    AAA = new_H_outline[2]
    BBB = (new_H_outline[1][0] + new_H_outline[4][0] - new_H_outline[5][0],
           new_H_outline[1][1] + new_H_outline[4][1] - new_H_outline[5][1])
    CCC = transform_point(rot_about(BBB, -math.pi/3), AAA)
    new_T_outline = [BBB, CCC, AAA]
    new_T = MetaTile(new_T_outline, "T")
    new_T.add_child(patch.children[11][0], patch.children[11][1])

    recentre(new_H)
    recentre(new_P)
    recentre(new_F)
    recentre(new_T)

    return [new_H, new_T, new_P, new_F]

# ==============================================================================
# DECOMPOSIÇÃO ATÉ NÍVEL 1
# ==============================================================================
def decompose_to_level1(meta, current_transform=(1, 0, 0, 0, 1, 0)):
    """Decompõe recursivamente um MetaTile até chegar aos metatiles de nível 1.

    Um metatile é 'nível 1' se NÃO tem filhos MetaTile (só HatLeaf ou vazio).
    Retorna lista de (transform_global, metatile_folha).
    """
    has_metatile_children = any(
        not isinstance(node, HatLeaf) for _, node in meta.children
    )

    if not has_metatile_children:
        return [(current_transform, meta)]

    result = []
    for T_child, node in meta.children:
        if isinstance(node, HatLeaf):
            continue
        T_global = mat_mul(current_transform, T_child)
        result.extend(decompose_to_level1(node, T_global))
    return result

# ==============================================================================
# GUILHOTINA: COHEN-SUTHERLAND PARA SEGMENTOS DE RETA
# ==============================================================================
INSIDE = 0
LEFT   = 1
RIGHT  = 2
BOTTOM = 4
TOP    = 8

def compute_outcode(x, y, xmin, ymin, xmax, ymax):
    code = INSIDE
    if x < xmin:      code |= LEFT
    elif x > xmax:    code |= RIGHT
    if y < ymin:      code |= BOTTOM
    elif y > ymax:    code |= TOP
    return code

def clip_line(x0, y0, x1, y1, xmin, ymin, xmax, ymax):
    """Cohen-Sutherland: recorta um segmento contra o retângulo.

    Retorna (x0, y0, x1, y1) se sobreviver, senão None.
    """
    outcode0 = compute_outcode(x0, y0, xmin, ymin, xmax, ymax)
    outcode1 = compute_outcode(x1, y1, xmin, ymin, xmax, ymax)
    accept = False

    while True:
        if not (outcode0 | outcode1):
            accept = True
            break
        elif outcode0 & outcode1:
            break
        else:
            x, y = 0.0, 0.0
            outcode_out = outcode0 if outcode0 else outcode1
            if outcode_out & TOP:
                x = x0 + (x1 - x0) * (ymax - y0) / (y1 - y0)
                y = ymax
            elif outcode_out & BOTTOM:
                x = x0 + (x1 - x0) * (ymin - y0) / (y1 - y0)
                y = ymin
            elif outcode_out & RIGHT:
                y = y0 + (y1 - y0) * (xmax - x0) / (x1 - x0)
                x = xmax
            elif outcode_out & LEFT:
                y = y0 + (y1 - y0) * (xmin - x0) / (x1 - x0)
                x = xmin

            if outcode_out == outcode0:
                x0, y0 = x, y
                outcode0 = compute_outcode(x0, y0, xmin, ymin, xmax, ymax)
            else:
                x1, y1 = x, y
                outcode1 = compute_outcode(x1, y1, xmin, ymin, xmax, ymax)

    return (x0, y0, x1, y1) if accept else None

# ==============================================================================
# SETA SIMPLIFICADA DE 10 PONTOS (TAMANHO FIXO)
# ==============================================================================
def make_arrow_10pts(center, direction, size):
    """Seta clássica de 10 pontos com tamanho FIXO (size em mm).

    Args:
        center: (cx, cy) centro da seta (mm)
        direction: (dx, dy) direção unitária
        size: comprimento total da seta em mm
    """
    cx, cy = center
    dx, dy = direction
    px, py = -dy, dx  # perpendicular

    shaft_len  = size * 0.55
    head_len   = size * 0.45
    shaft_half = size * 0.06
    head_half  = size * 0.20

    tail_x = cx - dx * shaft_len * 0.5
    tail_y = cy - dy * shaft_len * 0.5
    head_base_x = cx + dx * shaft_len * 0.5
    head_base_y = cy + dy * shaft_len * 0.5
    tip_x = cx + dx * (shaft_len * 0.5 + head_len)
    tip_y = cy + dy * (shaft_len * 0.5 + head_len)

    p1  = (tail_x + px * shaft_half,          tail_y + py * shaft_half)
    p2  = (head_base_x + px * shaft_half,     head_base_y + py * shaft_half)
    p3  = (head_base_x + px * head_half,      head_base_y + py * head_half)
    p4  = (head_base_x + px * head_half*0.5,  head_base_y + py * head_half*0.5)
    p5  = (tip_x,                             tip_y)
    p6  = (head_base_x - px * head_half*0.5,  head_base_y - py * head_half*0.5)
    p7  = (head_base_x - px * head_half,      head_base_y - py * head_half)
    p8  = (head_base_x - px * shaft_half,     head_base_y - py * shaft_half)
    p9  = (tail_x - px * shaft_half,          tail_y - py * shaft_half)
    p10 = (tail_x - px * shaft_half * 0.3,    tail_y - py * shaft_half * 0.3)

    return [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10]

# ==============================================================================
# ARESTA ALVO POR TIPO DE METATILE (conforme Figura 2.5 do artigo)
# ==============================================================================
# Cada entrada: (índice_vértice_A, índice_vértice_B) da aresta alvo
# Cada entrada: (índice_vértice_A, índice_vértice_B) da aresta alvo
# Os vértices seguem a ordem em *_OUTLINE
# Apenas H, T e P têm setas (F é parte do triskelion, sem seta)
# Cada entrada: (índice_vértice_A, índice_vértice_B) da aresta alvo
TARGET_EDGE = {
    'H': (0, 1),   # aresta superior direita
    'T': (0, 1),   # aresta base
    'P': (0, 1),   # aresta curta
    # 'F' NÃO tem entrada — peça F não recebe seta
}


def compute_arrow_for_piece(node, T, to_svg, arrow_size_mm):
    """Calcula posição e direção da seta para uma peça.

    A seta fica próxima ao centroide (não vaza da peça) e aponta na direção
    da aresta alvo.
    """
    # Garante que sempre há uma aresta alvo (fallback para H)
    label = node.label if node.label in TARGET_EDGE else 'H'
    iA, iB = TARGET_EDGE[label]

    # Pontos no espaço mundo
    pts_world = [transform_point(T, p) for p in node.shape]

    # Centroide
    cx_w = sum(p[0] for p in pts_world) / len(pts_world)
    cy_w = sum(p[1] for p in pts_world) / len(pts_world)

    # Ponto médio da aresta alvo
    A = pts_world[iA]
    B = pts_world[iB]
    mid_w = ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2)

    # Direção: do centroide para o ponto médio da aresta
    dx_w = mid_w[0] - cx_w
    dy_w = mid_w[1] - cy_w
    len_w = math.hypot(dx_w, dy_w)
    if len_w < 1e-9:
        dx_w, dy_w = 1.0, 0.0
    else:
        dx_w /= len_w
        dy_w /= len_w

    # Considerar reflexão da transformação
    a, b, c, d, e, f = T
    if a * e - b * d < 0:
        dx_w, dy_w = -dx_w, -dy_w

    # Seta fica a ~10% do caminho (bem perto do centroide, sem vazar)
    arrow_pos_w = (
        cx_w + dx_w * len_w * 0.10,
        cy_w + dy_w * len_w * 0.10,
    )

    center_svg = to_svg(arrow_pos_w)
    return center_svg, (dx_w, dy_w)

# ==============================================================================
# GERAÇÃO DO SVG
# ==============================================================================
def generate_svg(metatiles, output_path, sheet_width_cm, sheet_height_cm,
                 margin_mm, piece_size_cm):
    sheet_width  = sheet_width_cm * 10   # cm -> mm
    sheet_height = sheet_height_cm * 10
    margin = margin_mm

    xmin, ymin = margin, margin
    xmax, ymax = sheet_width - margin, sheet_height - margin

    print(f"Chapa:      {sheet_width:.0f} x {sheet_height:.0f} mm")
    print(f"Área útil:  {xmax - xmin:.0f} x {ymax - ymin:.0f} mm")

    # Escala baseada no tamanho da peça base (HAT)
    hat_diam = max(
        math.hypot(x1 - x2, y1 - y2)
        for i, (x1, y1) in enumerate(HAT_OUTLINE)
        for x2, y2 in HAT_OUTLINE[i+1:]
    )
    scale = piece_size_cm * 10 / hat_diam
    print(f"Escala:     {scale:.3f} mm/unidade (peça base: {piece_size_cm} cm)")

    if not metatiles:
        print("ERRO: nenhum metatile para desenhar.")
        return

    # Bounding box global (para centralizar na chapa)
    all_pts = []
    for T, node in metatiles:
        for p in node.shape:
            all_pts.append(transform_point(T, p))

    bb_min_x = min(p[0] for p in all_pts)
    bb_min_y = min(p[1] for p in all_pts)
    bb_max_x = max(p[0] for p in all_pts)
    bb_max_y = max(p[1] for p in all_pts)

    bb_cx = (bb_min_x + bb_max_x) / 2
    bb_cy = (bb_min_y + bb_max_y) / 2
    sheet_cx = (xmin + xmax) / 2
    sheet_cy = (ymin + ymax) / 2

    offset_x = sheet_cx - bb_cx * scale
    offset_y = sheet_cy - bb_cy * scale

    def to_svg(p):
        return (p[0] * scale + offset_x, p[1] * scale + offset_y)

    # ==========================================================
    # 1. FILTRO: manter apenas peças 100% dentro da área útil
    # ==========================================================
    valid_pieces = []
    pieces_outside = 0

    for T, node in metatiles:
        pts_svg = [to_svg(transform_point(T, p)) for p in node.shape]

        all_inside = all(
            xmin <= x <= xmax and ymin <= y <= ymax
            for x, y in pts_svg
        )
        if all_inside:
            valid_pieces.append((T, node, pts_svg))
        else:
            pieces_outside += 1

    print(f"  Peças 100% dentro:            {len(valid_pieces)}")
    print(f"  Peças fora/parcialmente fora: {pieces_outside}")

    # ==========================================================
    # 2. ARESTAS DE CORTE (deduplicadas globalmente)
    # ==========================================================
    unique_edges = set()

    for T, node, pts_svg in valid_pieces:
        n = len(pts_svg)
        for i in range(n):
            p1 = pts_svg[i]
            p2 = pts_svg[(i + 1) % n]
            rp1 = (round(p1[0], 3), round(p1[1], 3))
            rp2 = (round(p2[0], 3), round(p2[1], 3))
            # Ordenar garante que A->B e B->A sejam a mesma aresta
            edge = tuple(sorted([rp1, rp2]))
            unique_edges.add(edge)

    # ==========================================================
    # 3. SETAS: apenas em peças válidas; tamanho FIXO em mm
    # ==========================================================
        # ==========================================================
    # 3. SETAS: apenas em peças H, T, P (F não tem seta)
    # ==========================================================
    ARROW_SIZE_MM = 5.0

    arrow_segments = []

    for T, node, pts_svg in valid_pieces:
        # Pula peças F (parte do triskelion, sem seta)
        if node.label not in TARGET_EDGE:
            continue

        # Calcula posição e direção da seta (apontando para a aresta alvo)
        center_svg, direction = compute_arrow_for_piece(
            node, T, to_svg, ARROW_SIZE_MM
        )

        # Gera seta com TAMANHO FIXO
        arrow_pts = make_arrow_10pts(center_svg, direction, ARROW_SIZE_MM)

        # Converte polígono da seta em segmentos e clipa
        n_pts = len(arrow_pts)
        for i in range(n_pts):
            p1 = arrow_pts[i]
            p2 = arrow_pts[(i + 1) % n_pts]

            clipped = clip_line(p1[0], p1[1], p2[0], p2[1],
                                xmin, ymin, xmax, ymax)
            if clipped:
                cx1, cy1, cx2, cy2 = clipped
                if math.hypot(cx2 - cx1, cy2 - cy1) > 0.05:
                    arrow_segments.append((cx1, cy1, cx2, cy2))
                    
    # Deduplica segmentos de seta (evita gravação dupla sobreposta)
    unique_arrows = set()
    for (x1, y1, x2, y2) in arrow_segments:
        rp1 = (round(x1, 2), round(y1, 2))
        rp2 = (round(x2, 2), round(y2, 2))
        seg = tuple(sorted([rp1, rp2]))
        unique_arrows.add(seg)

    # ==========================================================
    # 4. GERAR SVG
    # ==========================================================
    cut_lines = []
    for (x1, y1), (x2, y2) in unique_edges:
        if math.hypot(x2 - x1, y2 - y1) > 0.01:
            cut_lines.append(
                f'  <line x1="{x1:.3f}" y1="{y1:.3f}" '
                f'x2="{x2:.3f}" y2="{y2:.3f}" '
                f'stroke="#000000" stroke-width="0.2" />'
            )

    arrow_lines = []
    for (x1, y1), (x2, y2) in unique_arrows:
        arrow_lines.append(
            f'  <line x1="{x1:.3f}" y1="{y1:.3f}" '
            f'x2="{x2:.3f}" y2="{y2:.3f}" '
            f'stroke="#0000ff" stroke-width="0.15" />'
        )

    border = (
        f'  <rect x="{xmin}" y="{ymin}" '
        f'width="{xmax - xmin}" height="{ymax - ymin}" '
        f'fill="none" stroke="#ff0000" stroke-width="0.3" '
        f'stroke-dasharray="5,5" />'
    )

    svg = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{sheet_width:.3f}mm" height="{sheet_height:.3f}mm" '
        f'viewBox="0 0 {sheet_width:.3f} {sheet_height:.3f}">',
        f'  <!-- Peças válidas: {len(valid_pieces)} -->',
        f'  <!-- Arestas de corte únicas: {len(cut_lines)} -->',
        f'  <!-- Segmentos de seta únicos: {len(arrow_lines)} -->',
        '  <g id="cuts">',
        *cut_lines,
        '  </g>',
        '  <g id="arrows">',
        *arrow_lines,
        '  </g>',
        border,
        '</svg>'
    ])

    Path(output_path).write_text(svg, encoding="utf-8")

    print()
    print(f"SVG gerado: {output_path}")
    print(f"  Arestas de corte:     {len(cut_lines)}")
    print(f"  Segmentos de seta:    {len(arrow_lines)}")

# ==============================================================================
# CLI
# ==============================================================================
def parse_args():
    parser = argparse.ArgumentParser(
        description="Gera SVG para corte a laser com metatiles de nível 1."
    )
    parser.add_argument("-o", "--output", default="laser_cut.svg",
                        help="Arquivo SVG de saída")
    parser.add_argument("--sheet-cm", nargs=2, type=float, metavar=("L", "A"),
                        default=[20.0, 20.0],
                        help="Tamanho da chapa em cm (largura altura)")
    parser.add_argument("--margin-mm", type=float, default=10.0,
                        help="Margem em mm")
    parser.add_argument("--size-cm", type=float, default=3.0,
                        help="Tamanho da peça base (HAT) em cm")
    parser.add_argument("--max-level", type=int, default=3,
                        help="Nível máximo de decomposição (0..N)")
    return parser.parse_args()

def main():
    args = parse_args()
    print("=" * 60)
    print("GERADOR DE SVG PARA CORTE A LASER")
    print("=" * 60)
    print(f"Chapa:      {args.sheet_cm[0]} x {args.sheet_cm[1]} cm")
    print(f"Margem:     {args.margin_mm} mm")
    print(f"Tamanho:    {args.size_cm} cm")
    print(f"Nível max:  {args.max_level}")
    print()

    # Inicializa metatiles
    tiles = [build_H_init(), build_T_init(), build_P_init(), build_F_init()]

    # Se max_level == 0, usa os metatiles base diretamente
    if args.max_level == 0:
        print("--- Nível 0 (metatiles base) ---")
        all_level1 = [((1, 0, 0, 0, 1, 0), t) for t in tiles]
        print(f"  Metatiles: {len(all_level1)}")
    else:
        # Itera até o nível desejado, mantendo APENAS o último patch
        patch = None
        for i in range(1, args.max_level + 1):
            print(f"--- Construindo nível {i} ---")
            patch = construct_patch(*tiles)
            tiles = construct_metatiles(patch)
            print(f"  Patch: {len(patch.children)} filhos")

        # Decompõe APENAS o patch final até nível 1
        print(f"\n--- Decompondo nível {args.max_level} até nível 1 ---")
        all_level1 = decompose_to_level1(patch)
        print(f"  Metatiles de nível 1: {len(all_level1)}")

    print()
    print("=" * 60)
    print(f"TOTAL de metatiles (nível 1): {len(all_level1)}")
    print("=" * 60)

    generate_svg(
        all_level1,
        args.output,
        args.sheet_cm[0],
        args.sheet_cm[1],
        args.margin_mm,
        args.size_cm
    )

if __name__ == "__main__":
    main()