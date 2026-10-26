# -*- coding: utf-8 -*-
"""
Figure 1 (revision R1, Reviewer 1 comment 5): research-methodology flowchart in engineering style
(ISO 5807 / ANSI symbols), black and white, built from NATIVE editable PowerPoint shapes and then
exported to 600-dpi PNG and PDF.
Symbols: terminator (start/end), parallelogram (input data), rectangle (process),
diamond (Yes/No decision), circle (connector A/B). Two-column layout to fit one page.
Outputs: flowchart.pptx/.png/.pdf. The export step uses PowerPoint COM (Windows) and closes
PowerPoint when it finishes; save other open presentations first.
"""
import os
import re
import subprocess

from pptx import Presentation
from pptx.util import Mm, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
W_MM, H_MM = 176, 166
HITAM = RGBColor(0, 0, 0)
PUTIH = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Times New Roman"

prs = Presentation()
prs.slide_width, prs.slide_height = Mm(W_MM), Mm(H_MM)
sl = prs.slides.add_slide(prs.slide_layouts[6])


def bentuk(jenis, x, y, w, h, teks, size=8.0, bold=False):
    s = sl.shapes.add_shape(jenis, Mm(x), Mm(y), Mm(w), Mm(h))
    s.fill.solid(); s.fill.fore_color.rgb = PUTIH
    s.line.color.rgb = HITAM; s.line.width = Pt(0.9)
    s.shadow.inherit = False
    tf = s.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, Mm(0.8))
    for k, baris in enumerate(teks.split("\n")):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        for k2, bagian in enumerate(re.split(r"_\{([^}]*)\}", baris)):   # X_{sub} -> subskrip
            if not bagian:
                continue
            r = p.add_run(); r.text = bagian
            r.font.size = Pt(size); r.font.name = FONT; r.font.bold = bold; r.font.color.rgb = HITAM
            if k2 % 2 == 1:
                r._r.get_or_add_rPr().set("baseline", "-25000")
    return s


def garis(pts, panah=True):
    for i in range(len(pts) - 1):
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        c = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Mm(x1), Mm(y1), Mm(x2), Mm(y2))
        c.line.color.rgb = HITAM; c.line.width = Pt(0.9)
        c.shadow.inherit = False
        if panah and i == len(pts) - 2:
            ln = c.line._get_or_add_ln()
            ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))


def label(x, y, teks, size=7.5):
    tb = sl.shapes.add_textbox(Mm(x), Mm(y), Mm(9), Mm(4))
    tf = tb.text_frame
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, 0)
    r = tf.paragraphs[0].add_run(); r.text = teks
    r.font.size = Pt(size); r.font.name = FONT; r.font.italic = True; r.font.color.rgb = HITAM


def konektor(cx, cy, huruf):
    return bentuk(MSO_SHAPE.FLOWCHART_CONNECTOR, cx - 3, cy - 3, 6, 6, huruf, size=8, bold=True)


# ------------------------------------------------------------------ kolom kiri
XL, WL = 8, 66
CL = XL + WL / 2
bentuk(MSO_SHAPE.FLOWCHART_TERMINATOR, CL - 15, 3, 30, 7, "Start", bold=True)
bentuk(MSO_SHAPE.FLOWCHART_DATA, XL, 14, WL, 13,
       "Input: plant and grid parameters,\nscenarios S1–S5 (Table 2)")
bentuk(MSO_SHAPE.FLOWCHART_PROCESS, XL, 31, WL, 14,
       "Averaged PV–BESS model: single-diode PV,\nP&O MPPT, battery SOC, PLL, VIC and\naggregate swing equation (Python and Julia)")
bentuk(MSO_SHAPE.FLOWCHART_PROCESS, XL, 49, WL, 12,
       "Coordination law: severity weight α (3), SOC-aware\ngate β (4), reference P_{ref} (5); four baselines")
bentuk(MSO_SHAPE.FLOWCHART_PROCESS, XL, 65, WL, 12,
       "Robust tuning: Monte Carlo sampling with CVaR\n(γ = 0.95), NSGA-II, knee-point gain set")
# gerbang verifikasi SESUDAH penalaan: trajektori kelima kontroler (gain knee) dibandingkan
# Python–Julia, ditambah RoCoF awal terhadap prediksi analitis (Section 4.2)
bentuk(MSO_SHAPE.FLOWCHART_DECISION, CL - 28, 81, 56, 22,
       "Python–Julia bit-exact\nand initial RoCoF within\n0.5 % of ΔP/(2H_{sys})?", size=7.2)
bentuk(MSO_SHAPE.FLOWCHART_PROCESS, XL, 107, WL, 16,
       "Scenario evaluation: S1–S5 × five controllers\n× 100 realisations; nadir, RoCoF, MPP deviation,\nBESS throughput; effect sizes (Cliff's δ)")
garis([(CL, 10), (CL, 14)])
garis([(CL, 27), (CL, 31)])
garis([(CL, 45), (CL, 49)])
garis([(CL, 61), (CL, 65)])
garis([(CL, 77), (CL, 81)])
garis([(CL, 103), (CL, 107)]); label(CL + 1.5, 102.8, "Yes")
garis([(CL - 28, 92), (3.5, 92), (3.5, 38), (XL, 38)]); label(CL - 33, 88.1, "No")
garis([(CL, 123), (CL, 126.5)])
konektor(CL, 129.5, "A")
konektor(XL + WL + 6.5, 38, "B")
garis([(XL + WL + 3.5, 38), (XL + WL, 38)])

# ------------------------------------------------------------------ kolom kanan
XR, WR = 92, 66
CR = XR + WR / 2
konektor(CR, 5, "A")
garis([(CR, 8), (CR, 12)])
bentuk(MSO_SHAPE.FLOWCHART_PROCESS, XR, 12, WR, 12,
       "Spectral limit-cycle test for each controller:\nP_{p2p} > 0.01 pu and f_{osc} > 2/T_{w} (6–8 s)")
garis([(CR, 24), (CR, 27)])
# keputusan: cabang Yes/No turun LURUS dari sudut kiri/kanan belah ketupat ke kotak tepat di bawahnya
DW, DH = 44, 26
VY = 27 + DH / 2                   # tinggi sudut kiri/kanan
VL, VR = CR - DW / 2, CR + DW / 2  # x sudut kiri/kanan
bentuk(MSO_SHAPE.FLOWCHART_DECISION, CR - DW / 2, 27, DW, DH,
       "Threshold\n(relay) battery\ndispatch?", size=7.5)
YB, BW, BH = 57, 38, 20
OFS = 8                           # kotak cabang bergeser keluar dari sudut
XBL, XBR = VL - OFS, VR + OFS      # pusat kotak cabang kiri/kanan
bentuk(MSO_SHAPE.FLOWCHART_PROCESS, XBL - BW / 2, YB, BW, BH,
       "Describing function and\nexistence condition (6),\nchecked against detected\ncycles (Figure 7)", size=7.3)
bentuk(MSO_SHAPE.FLOWCHART_PROCESS, XBR - BW / 2, YB, BW, BH,
       "Circle criterion: absence\ncertificate for smooth,\nsector-bounded dispatch,\nchecked against test", size=7.3)
garis([(VL, VY), (XBL, VY), (XBL, YB)]); label(XBL - 1, VY - 4.5, "Yes")   # ke samping dulu, lalu turun
garis([(VR, VY), (XBR, VY), (XBR, YB)]); label(XBR - 4, VY - 4.5, "No")
garis([(XBL, YB + BH), (XBL, 79), (CR, 79)], panah=False)
garis([(XBR, YB + BH), (XBR, 79), (CR, 79)], panah=False)
garis([(CR, 79), (CR, 82)])
bentuk(MSO_SHAPE.FLOWCHART_PROCESS, XR, 82, WR, 18,
       "Robustness checks: relay at 49.7 Hz and latched\nFFR, primary reserve (map and S3–S4 runs),\nablation of α and of the gate, SOC near its\nlimits, inertia sweep, load rejection (S6)")
garis([(CR, 100), (CR, 103)])
bentuk(MSO_SHAPE.FLOWCHART_PROCESS, XR, 103, WR, 12,
       "Switching-level testbed: coupled battery converter,\nswing-equation grid emulator (Simulink)")
garis([(CR, 115), (CR, 118)])
bentuk(MSO_SHAPE.FLOWCHART_DECISION, CR - 28, 118, 56, 20, "Nadir and P_{p2p} agree\nwith averaged model?", size=7.5)
garis([(CR + 28, 128), (CR + 33.5, 128)]); label(CR + 28.5, 124, "No")
konektor(CR + 36.5, 128, "B")
garis([(CR, 138), (CR, 142)]); label(CR + 1.5, 138.5, "Yes")
bentuk(MSO_SHAPE.FLOWCHART_PROCESS, XR, 142, WR, 11,
       "Comparison with previous studies,\nlimitations and conclusions")
garis([(CR, 153), (CR, 157)])
bentuk(MSO_SHAPE.FLOWCHART_TERMINATOR, CR - 15, 157, 30, 7, "End", bold=True)

out = os.path.join(HERE, "flowchart.pptx")
prs.save(out)
ps = f"""
$pp = New-Object -ComObject PowerPoint.Application
$p = $pp.Presentations.Open('{out}', $true, $false, $false)
$p.Slides(1).Export('{os.path.join(HERE, "flowchart.png")}', 'PNG', {int(W_MM / 25.4 * 600)}, {int(H_MM / 25.4 * 600)})
$p.SaveAs('{os.path.join(HERE, "flowchart.pdf")}', 32)
$p.Close(); $pp.Quit()
"""
subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
print("ok")
