#!/usr/bin/env python3
"""Gera SVGs de polykites (Hat) usando Sistema-L com subdivisão adaptativa."""

import argparse
import math
from pathlib import Path

SQRT3 = math.sqrt(3)
HR3 = SQRT3 / 2

# --- Geometria Base ---
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

# --- Operações de Matrizes Afins ---
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
    return (e/det, -b/det, (b*f - e*c)/det, -d/det, a/det, (d*c - a*f)/det)

def transform_point(T, p):
    a, b, c, d, e, f = T
    return (a*p[0] + b*p[1] + c, d*p[0] + e*p[1] + f)

def match_seg(p, q):
    return (q[0]-p[0], p[1]-q[1], p[0], q[1]-p[1], q[0]-p[0], p[1])

def match_two(p1, q1, p2, q2):
    return mat_mul(match_seg(p2, q2), mat_inv(match_seg(p1, q1)))

def get_bbox(shape, transform):
    """Retorna (min_x, min_y, max_x, max_y) de um shape transformado."""
    pts = [transform_point(transform, p) for p in shape]
    min_x = min(p[0] for p in pts)
    min_y = min(p[1] for p in pts)
    max_x = max(p[0] for p in pts)
    max_y = max(p[1] for p in pts)
    return min_x, min_y, max_x, max_y

def bbox_intersects(bbox1, bbox2):
    """Verifica se dois bounding boxes se intersectam."""
    min_x1, min_y1, max_x1, max_y1 = bbox1
    min_x2, min_y2, max_x2, max_y2 = bbox2
    return not (max_x1 < min_x2 or max_x2 < min_x1 or max_y1 < min_y2 or max_y2 < min_y1)

# --- Classes do Sistema-L ---
class HatLeaf:
    def __init__(self, label, reflected=False):
        self.label = label
        self.reflected = reflected

class MetaTile:
    def __init__(self, shape):
        self.shape = shape
        self.children = []
        
    def add_child(self, transform, node):
        self.children.append((transform, node))

def recentre(meta):
    cx = sum(p[0] for p in meta.shape) / len(meta.shape)
    cy = sum(p[1] for p in meta.shape) / len(meta.shape)
    meta.shape = [(p[0]-cx, p[1]-cy) for p in meta.shape]
    T_trans = (1, 0, -cx, 0, 1, -cy)
    meta.children = [(mat_mul(T_trans, T), node) for T, node in meta.children]

# --- Inicialização dos Metatiles (Nível 1) ---
def build_H_init():
    meta = MetaTile(H_OUTLINE)
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
    meta = MetaTile(T_OUTLINE)
    meta.add_child((0.5, 0, 0.5, 0, 0.5, HR3), HatLeaf("T"))
    recentre(meta)
    return meta

def build_P_init():
    meta = MetaTile(P_OUTLINE)
    meta.add_child((0.5, 0, 1.5, 0, 0.5, HR3), HatLeaf("P"))
    T1 = (0.5, HR3, 0, -HR3, 0.5, 0)
    T2 = (0.5, 0, 0, 0, 0.5, 0)
    T3 = (1, 0, 0, 0, 1, 2 * HR3)
    meta.add_child(mat_mul(T3, mat_mul(T1, T2)), HatLeaf("P"))
    recentre(meta)
    return meta

def build_F_init():
    meta = MetaTile(F_OUTLINE)
    meta.add_child((0.5, 0, 1.5, 0, 0.5, HR3), HatLeaf("F"))
    T1 = (0.5, HR3, 0, -HR3, 0.5, 0)
    T2 = (0.5, 0, 0, 0, 0.5, 0)
    T3 = (1, 0, 0, 0, 1, 2 * HR3)
    meta.add_child(mat_mul(T3, mat_mul(T1, T2)), HatLeaf("F"))
    recentre(meta)
    return meta

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
    ret = MetaTile([])
    shapes = {'H': H, 'T': T, 'P': P, 'F': F}
    ident = (1, 0, 0, 0, 1, 0)
    
    for r in rules:
        if len(r) == 1:
            ret.add_child(ident, shapes[r[0]])
        elif len(r) == 4:
            p_idx, p_edge, c_type, c_edge = r
            poly = ret.children[p_idx][1].shape
            T_parent = ret.children[p_idx][0]
            P_pt = transform_point(T_parent, poly[(p_edge+1)%len(poly)])
            Q = transform_point(T_parent, poly[p_edge])
            nshp = shapes[c_type]
            T_child = match_two(nshp.shape[c_edge], nshp.shape[(c_edge+1)%len(nshp.shape)], P_pt, Q)
            ret.add_child(T_child, nshp)
        else:
            p_idx, p_edge, q_idx, q_edge, c_type, c_edge = r
            chP = ret.children[p_idx]
            chQ = ret.children[q_idx]
            P_pt = transform_point(chQ[0], chQ[1].shape[q_edge])
            Q = transform_point(chP[0], chP[1].shape[p_edge])
            nshp = shapes[c_type]
            T_child = match_two(nshp.shape[c_edge], nshp.shape[(c_edge+1)%len(nshp.shape)], P_pt, Q)
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
    
    new_H = MetaTile(new_H_outline)
    for ch in [0, 9, 16, 27, 26, 6, 1, 8, 10, 15]:
        new_H.add_child(patch.children[ch][0], patch.children[ch][1])
        
    v = (bps1[0] - llc[0], bps1[1] - llc[1])
    new_P_outline = [p72, (p72[0] + v[0], p72[1] + v[1]), bps1, llc]
    new_P = MetaTile(new_P_outline)
    for ch in [7, 2, 3, 4, 28]:
        new_P.add_child(patch.children[ch][0], patch.children[ch][1])
        
    v2 = (llc[0] - bps1[0], llc[1] - bps1[1])
    new_F_outline = [bps2, eval_child(24, 2), eval_child(25, 0), p252, (p252[0] + v2[0], p252[1] + v2[1])]
    new_F = MetaTile(new_F_outline)
    for ch in [21, 20, 22, 23, 24, 25]:
        new_F.add_child(patch.children[ch][0], patch.children[ch][1])
        
    AAA = new_H_outline[2]
    BBB = (new_H_outline[1][0] + new_H_outline[4][0] - new_H_outline[5][0], 
           new_H_outline[1][1] + new_H_outline[4][1] - new_H_outline[5][1])
    CCC = transform_point(rot_about(BBB, -math.pi/3), AAA)
    new_T_outline = [BBB, CCC, AAA]
    new_T = MetaTile(new_T_outline)
    new_T.add_child(patch.children[11][0], patch.children[11][1])
    
    recentre(new_H)
    recentre(new_P)
    recentre(new_F)
    recentre(new_T)
    
    return [new_H, new_T, new_P, new_F]

# --- SUBDIVISÃO ADAPTATIVA ---
def adaptive_subdivide(meta, transform, target_bbox, current_level, max_level):
    """
    Subdivide recursivamente apenas os tiles que intersectam a área alvo.
    Retorna lista de (transform, HatLeaf) no nível final.
    """
    # CORREÇÃO: Verificar se é HatLeaf ANTES de acessar .shape
    if isinstance(meta, HatLeaf):
        bbox = get_bbox(HAT_OUTLINE, transform)
        if bbox_intersects(bbox, target_bbox):
            return [(transform, meta)]
        return []
    
    # Agora é seguro acessar meta.shape (é MetaTile)
    bbox = get_bbox(meta.shape, transform)
    
    # Se não intersecta a área alvo, descarta completamente
    if not bbox_intersects(bbox, target_bbox):
        return []
    
    # Se atingiu o nível máximo, expande todos os filhos
    if current_level >= max_level:
        hats = []
        for T_child, node in meta.children:
            T_global = mat_mul(transform, T_child)
            hats.extend(adaptive_subdivide(node, T_global, target_bbox, current_level + 1, max_level))
        return hats
    
    # Caso contrário, verifica cada filho recursivamente
    hats = []
    for T_child, node in meta.children:
        T_global = mat_mul(transform, T_child)
        hats.extend(adaptive_subdivide(node, T_global, target_bbox, current_level + 1, max_level))
    
    return hats

def diameter(points):
    return max(math.hypot(x1 - x2, y1 - y2) for i, (x1, y1) in enumerate(points) for x2, y2 in points[i + 1:])

def parse_args():
    parser = argparse.ArgumentParser(description="Gera SVGs via Sistema-L com subdivisão adaptativa.")
    parser.add_argument("-o", "--output", default="azulejos_adaptativo.svg")
    parser.add_argument("--sheet-cm", nargs=2, type=float, metavar=("L", "A"), default=[40.0, 40.0])
    parser.add_argument("--margin-mm", type=float, default=20.0)
    parser.add_argument("--size-cm", type=float, default=5.0)
    return parser.parse_args()

def main():
    args = parse_args()
    sheet_width = args.sheet_cm[0] * 10
    sheet_height = args.sheet_cm[1] * 10
    margin = args.margin_mm
    scale_mm = args.size_cm * 10 / diameter(HAT_OUTLINE)
    
    print("Gerando estrutura fractal (4 iterações)...")
    tiles = [build_H_init(), build_T_init(), build_P_init(), build_F_init()]
    patch = None
    for i in range(4):
        print(f"  Iteração {i+1}/4...")
        patch = construct_patch(*tiles)
        tiles = construct_metatiles(patch)
    
    # Define a área alvo (em coordenadas do patch, antes da escala)
    sheet_cx, sheet_cy = sheet_width / 2, sheet_height / 2
    
    # Calcula bounding box aproximada do patch gigante (nível 4)
    test_bbox = get_bbox(tiles[0].shape, (1, 0, 0, 0, 1, 0))
    patch_cx = (test_bbox[0] + test_bbox[2]) / 2
    patch_cy = (test_bbox[1] + test_bbox[3]) / 2
    
    # Área alvo em coordenadas do patch
    target_min_x = (margin - sheet_cx) / scale_mm + patch_cx
    target_min_y = (margin - sheet_cy) / scale_mm + patch_cy
    target_max_x = (sheet_width - margin - sheet_cx) / scale_mm + patch_cx
    target_max_y = (sheet_height - margin - sheet_cy) / scale_mm + patch_cy
    target_bbox = (target_min_x, target_min_y, target_max_x, target_max_y)
    
    print(f"Área alvo (coordenadas do patch): x=[{target_min_x:.2f}, {target_max_x:.2f}], y=[{target_min_y:.2f}, {target_max_y:.2f}]")
    
    # SUBDIVISÃO ADAPTATIVA: Começa do nível 4 (supertile) e desce até o nível 0 (tile)
    print("Aplicando subdivisão adaptativa...")
    hats = adaptive_subdivide(tiles[0], (1, 0, 0, 0, 1, 0), target_bbox, 0, 4)
    print(f"Total de peças após subdivisão adaptativa: {len(hats)}")
    
    # FILTRA PEÇAS INTEIRAS E DEPOIS DESMANCHA EM LINHAS ÚNICAS
    unique_edges = set()
    xmin, ymin = margin, margin
    xmax, ymax = sheet_width - margin, sheet_height - margin
    
    for T_mat, _ in hats:
        pts = [transform_point(T_mat, p) for p in HAT_OUTLINE]
        
        # 1. Verifica se TODOS os pontos do chapéu estão dentro da margem
        scaled_pts = []
        is_inside = True
        for p in pts:
            x = (p[0] - patch_cx) * scale_mm + sheet_cx
            y = (p[1] - patch_cy) * scale_mm + sheet_cy
            
            # Se qualquer vértice vazar a margem, a peça inteira é invalidada
            if x < xmin or x > xmax or y < ymin or y > ymax:
                is_inside = False
                break
            scaled_pts.append((x, y))
            
        # 2. Se a peça inteira couber perfeitamente, extrai suas linhas para deduplicação
        if is_inside:
            for i in range(len(scaled_pts)):
                p1 = scaled_pts[i]
                p2 = scaled_pts[(i+1) % len(scaled_pts)]
                
                # Arredonda e ordena para que linhas sobrepostas sejam idênticas no Set
                edge = tuple(sorted([(round(p1[0], 4), round(p1[1], 4)), (round(p2[0], 4), round(p2[1], 4))]))
                unique_edges.add(edge)
                
    # Converte o conjunto de linhas únicas para caminhos SVG
    valid_paths = [
        f'  <line x1="{x1:.4f}" y1="{y1:.4f}" x2="{x2:.4f}" y2="{y2:.4f}" />'
        for (x1, y1), (x2, y2) in unique_edges
    ]
    
    print(f"Linhas finais para o laser (apenas peças inteiras e sem duplicatas): {len(valid_paths)}")
    
    # Retângulo de margem para visualização
    margin_rect = (
        f'  <rect x="{margin:.4f}" y="{margin:.4f}" '
        f'width="{sheet_width - 2*margin:.4f}" height="{sheet_height - 2*margin:.4f}" '
        f'fill="none" stroke="#ff0000" stroke-width="0.2" stroke-dasharray="4,4" />'
    )
    
    # Gera o SVG completo
    svg = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{sheet_width:.4f}mm" height="{sheet_height:.4f}mm" viewBox="0 0 {sheet_width:.4f} {sheet_height:.4f}">',
        '  <g fill="none" stroke="#000000" stroke-width="0.1">',
        *valid_paths,
        '  </g>',
        margin_rect,
        '</svg>'
    ])
    
    Path(args.output).write_text(svg, encoding="utf-8")
    print(f"SVG gerado com sucesso em: {args.output}")

if __name__ == "__main__":
    main()