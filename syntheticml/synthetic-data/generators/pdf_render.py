"""ReportLab rendering of synthetic invoice documents (12 original layouts,
docs/invoice-layout-guide.md). SYNTHETIC — EPRLens Demo.

The renderer draws ONLY strings already present in the document model built by
documents.py, so the PDF and its ground-truth JSON cannot diverge. Standard PDF
fonts only (no embedding); invariant=1 gives byte-reproducible files.
"""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

WATERMARK = "SYNTHETIC — EPRLens Demo"

COLS = {
    "no": ("#", 18, "L"), "desc": ("Description", None, "L"), "hsn": ("HSN/SAC", 44, "L"),
    "mat": ("Material", 48, "L"), "cat": ("EPR Cat", 42, "L"), "qty": ("Qty", 62, "R"), "unit": ("Unit", 34, "L"),
    "wpu": ("g/unit", 38, "R"), "rate": ("Rate", 56, "R"), "amt": ("Amount", 82, "R"), "gst": ("GST%", 30, "R"),
    "tax": ("Tax", 62, "R"),
}

LAYOUTS = {
    "L01": dict(name="Simple GST invoice", cols=["no", "desc", "hsn", "qty", "unit", "rate", "amt"], header="simple",
                font="Helvetica", size=8, words=True),
    "L02": dict(name="Modern corporate", cols=["no", "desc", "mat", "cat", "qty", "unit", "rate", "amt"], header="band",
                font="Helvetica", size=8),
    "L03": dict(name="Dense table", cols=["no", "desc", "hsn", "mat", "cat", "qty", "unit", "wpu", "rate", "amt", "gst", "tax"],
                header="simple", font="Helvetica", size=6.5, landscape=True, capacity=8),
    "L04": dict(name="Two-column header", cols=["no", "desc", "hsn", "qty", "unit", "rate", "amt"], header="twocol",
                font="Times-Roman", size=8.5),
    "L05": dict(name="Multi-page", cols=["no", "desc", "hsn", "cat", "qty", "unit", "rate", "amt"], header="simple",
                font="Helvetica", size=8, capacity=5),
    "L06": dict(name="QR placeholder", cols=["no", "desc", "hsn", "qty", "unit", "rate", "amt"], header="qr",
                font="Helvetica", size=8, words=True),
    "L07": dict(name="Bank-details block", cols=["no", "desc", "mat", "qty", "unit", "wpu", "rate", "amt"], header="simple",
                font="Helvetica", size=8, bank=True),
    "L08": dict(name="Billing + shipping", cols=["no", "desc", "hsn", "qty", "unit", "rate", "amt"], header="threeparty",
                font="Helvetica", size=8),
    "L09": dict(name="Tax summary", cols=["no", "desc", "cat", "qty", "unit", "rate", "amt"], header="simple",
                font="Helvetica", size=8, tax_summary=True),
    "L10": dict(name="Recycler service", cols=["no", "desc", "cat", "qty", "unit", "rate", "amt"], header="recycler",
                font="Helvetica", size=7.5),
    "L11": dict(name="Minimal plain text", cols=[], header="plain", font="Courier", size=8, capacity=6),
    "L12": dict(name="Import commercial", cols=["no", "desc", "hsn", "cat", "qty", "unit", "rate", "amt"], header="import",
                font="Helvetica", size=8),
}
HEADER_LABELS = {"L12": {"hsn": "HS code", "rate": "Unit price", "amt": "Amount"}}
PRINTS_HSN = {"L01", "L03", "L04", "L05", "L06", "L08", "L11", "L12"}
PRINTS_CATEGORY = {"L02", "L03", "L05", "L09", "L10", "L11", "L12"}
PRINTS_MATERIAL_COLUMN = {"L02", "L03", "L07"}
PRINTS_WPU_COLUMN = {"L03", "L07"}


def capacity(layout):
    return LAYOUTS[layout].get("capacity", 12)


def wrap(text, font, size, width, max_lines=3):
    words, lines, cur = text.split(" "), [], ""
    for wd in words:
        trial = wd if not cur else cur + " " + wd
        if stringWidth(trial, font, size) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    return lines


class Pdf:
    def __init__(self, path, doc):
        self.doc = doc
        self.lay = LAYOUTS[doc["template_id"]]
        size = landscape(A4) if self.lay.get("landscape") else A4
        self.W, self.H = size
        self.c = canvas.Canvas(str(path), pagesize=size, invariant=1, pageCompression=0)
        self.c.setTitle(doc["invoice_number_printed"] or doc["document_id"])
        self.c.setAuthor("EPRLens synthetic generator")
        self.c.setSubject(WATERMARK)
        self.c.setKeywords(["synthetic", "EPRLens", "demo"])
        self.font, self.fsize = self.lay["font"], self.lay["size"]
        self.bold = {"Helvetica": "Helvetica-Bold", "Times-Roman": "Times-Bold", "Courier": "Courier-Bold"}[self.font]
        self.m = 36

    # ------------------------------------------------------------ primitives
    def text(self, x, y, s, size=None, bold=False, align="L"):
        if s is None or s == "":
            return
        self.c.setFont(self.bold if bold else self.font, size or self.fsize)
        if align == "R":
            self.c.drawRightString(x, y, s)
        elif align == "C":
            self.c.drawCentredString(x, y, s)
        else:
            self.c.drawString(x, y, s)

    def page_frame(self, n, total):
        c = self.c
        c.saveState()
        c.setFillColorRGB(0.86, 0.86, 0.86)
        c.setFont("Helvetica-Bold", 40)
        c.translate(self.W / 2, self.H / 2)
        c.rotate(33)
        c.drawCentredString(0, 0, WATERMARK)
        c.restoreState()
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 7)
        c.drawCentredString(self.W / 2, 18, f"{WATERMARK} · {self.doc['document_id']} · page {n}/{total}")
        if self.doc["status"] == "cancelled":
            c.saveState()
            c.setFillColorRGB(0.8, 0.1, 0.1)
            c.setStrokeColorRGB(0.8, 0.1, 0.1)
            c.translate(self.W - 170, self.H - 150)
            c.rotate(18)
            c.rect(-10, -8, 130, 30, fill=0)
            c.setFont("Helvetica-Bold", 20)
            c.drawString(0, 0, "CANCELLED")
            c.restoreState()
            c.setFillColorRGB(0, 0, 0)

    def party_block(self, x, y, label, p, width):
        self.text(x, y, label, bold=True, size=self.fsize)
        y -= self.fsize + 3
        self.text(x, y, p["name"], bold=True)
        y -= self.fsize + 2
        for line in p["address_lines"]:
            for part in wrap(line, self.font, self.fsize, width, 2):
                self.text(x, y, part)
                y -= self.fsize + 2
        if p.get("gstin_line"):
            self.text(x, y, p["gstin_line"])
            y -= self.fsize + 2
        for extra in p.get("extra_lines", []):
            self.text(x, y, extra)
            y -= self.fsize + 2
        return y

    def meta_block(self, x, y, align="L"):
        for label, value in self.doc["meta"]:
            self.text(x, y, f"{label}: {value}" if value != "" else f"{label}:", align=align)
            y -= self.fsize + 3
        return y

    # ------------------------------------------------------------ headers
    def header(self):
        d, W, H, m = self.doc, self.W, self.H, self.m
        style = self.lay["header"]
        y = H - m
        if style == "band":
            self.c.setFillColorRGB(0.08, 0.5, 0.24)
            self.c.rect(0, H - 70, W, 70, fill=1, stroke=0)
            self.c.setFillColorRGB(1, 1, 1)
            self.c.circle(m + 18, H - 35, 16, fill=0, stroke=1)
            self.text(m + 18, H - 39, d["issuer"]["initials"], size=11, bold=True, align="C")
            self.text(m + 44, H - 32, d["issuer"]["name"], size=12, bold=True)
            self.text(W - m, H - 32, d["title"], size=14, bold=True, align="R")
            self.c.setFillColorRGB(0, 0, 0)
            y = H - 90
            yl = self.party_block(m, y, "From", d["issuer"], 240)
            yr = self.meta_block(W - m, y, align="R")
            y = min(yl, yr) - 6
            y = self.party_block(m, y, "Bill to", d["recipient"], 300) - 6
        elif style == "twocol":
            self.text(W / 2, y, d["title"], size=13, bold=True, align="C")
            y -= 24
            half = (W - 2 * m) / 2
            yl = self.party_block(m, y, "Supplier", d["issuer"], half - 10)
            yr = self.party_block(m + half + 10, y, "Recipient", d["recipient"], half - 10)
            y = min(yl, yr) - 6
            for label, value in d["meta"]:
                pass
            row = "    ".join(f"{label}: {value}" for label, value in d["meta"])
            for part in wrap(row, self.font, self.fsize, W - 2 * m, 3):
                self.text(m, y, part)
                y -= self.fsize + 3
            y -= 4
        elif style == "threeparty":
            self.text(W / 2, y, d["title"], size=13, bold=True, align="C")
            y -= 22
            third = (W - 2 * m) / 3
            y1 = self.party_block(m, y, "Seller", d["issuer"], third - 8)
            y2 = self.party_block(m + third, y, "Bill to", d["recipient"], third - 8)
            y3 = self.party_block(m + 2 * third, y, "Ship to", d.get("ship_to") or d["recipient"], third - 8)
            y = min(y1, y2, y3) - 6
            y = self.meta_block(m, y) - 4
        elif style == "qr":
            self.c.setFillColorRGB(0.9, 0.9, 0.9)
            self.c.rect(W - m - 90, H - m - 90, 90, 90, fill=1, stroke=1)
            self.c.setFillColorRGB(0, 0, 0)
            self.text(W - m - 45, H - m - 40, "QR - SYNTHETIC", size=7, align="C")
            self.text(W - m - 45, H - m - 50, "(not scannable)", size=7, align="C")
            self.text(m, y, d["title"], size=14, bold=True)
            y -= 14
            self.text(m, y, "IRN: SYNTHETIC-NOT-AN-IRN", size=7)
            y -= 18
            y = self.party_block(m, y, "Seller", d["issuer"], 300) - 4
            y = min(y, H - m - 100)
            yl = self.party_block(m, y, "Buyer", d["recipient"], 280)
            yr = self.meta_block(W - m, y, align="R")
            y = min(yl, yr) - 6
        elif style == "recycler":
            self.text(m, y, d["issuer"]["name"], size=12, bold=True)
            y -= 14
            for line in d["issuer"]["address_lines"]:
                self.text(m, y, line)
                y -= self.fsize + 2
            self.text(m, y, d["issuer"].get("gstin_line", ""))
            y -= self.fsize + 2
            for extra in d["issuer"].get("extra_lines", []):
                self.text(m, y, extra, bold=True)
                y -= self.fsize + 2
            self.text(W - m, H - m, d["title"], size=13, bold=True, align="R")
            y -= 6
            yl = self.party_block(m, y, "Client", d["recipient"], 280)
            yr = self.meta_block(W - m, y, align="R")
            y = min(yl, yr) - 6
        elif style == "import":
            self.text(W / 2, y, d["title"], size=14, bold=True, align="C")
            y -= 24
            half = (W - 2 * m) / 2
            yl = self.party_block(m, y, "Exporter", d["issuer"], half - 10)
            yr = self.party_block(m + half + 10, y, "Consignee / Importer", d["recipient"], half - 10)
            y = min(yl, yr) - 6
            y = self.meta_block(m, y) - 4
        elif style == "plain":
            self.text(m, y, "=" * 70)
            y -= 12
            self.text(m, y, d["title"], bold=True)
            y -= 14
            for label, p in (("FROM", d["issuer"]), ("TO", d["recipient"])):
                self.text(m, y, f"{label}: {p['name']}")
                y -= 11
                for line in p["address_lines"]:
                    self.text(m + 40, y, line[:70])
                    y -= 11
                if p.get("gstin_line"):
                    self.text(m + 40, y, p["gstin_line"])
                    y -= 11
            for label, value in d["meta"]:
                self.text(m, y, f"{label}: {value}")
                y -= 11
            self.text(m, y, "-" * 70)
            y -= 14
        else:  # simple
            self.text(W / 2, y, d["title"], size=14, bold=True, align="C")
            y -= 22
            yl = self.party_block(m, y, "Seller", d["issuer"], 280)
            yr = self.meta_block(W - m, y, align="R")
            y = min(yl, yr) - 6
            y = self.party_block(m, y, "Buyer", d["recipient"], 300) - 6
        return y

    # ------------------------------------------------------------ table
    def col_layout(self):
        keys = self.lay["cols"]
        fixed = sum(COLS[k][1] for k in keys if COLS[k][1])
        flex = (self.W - 2 * self.m) - fixed
        out, x = [], self.m
        for k in keys:
            wdt = COLS[k][1] or flex
            out.append((k, x, wdt, COLS[k][2]))
            x += wdt
        return out

    def table_header(self, y, cols):
        c = self.c
        h = self.fsize + 6
        c.setFillColorRGB(0.88, 0.92, 0.89)
        c.rect(self.m, y - h + self.fsize, self.W - 2 * self.m, h, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        labels = HEADER_LABELS.get(self.doc["template_id"], {})
        for k, x, wdt, al in cols:
            label = labels.get(k, COLS[k][0])
            if k in ("rate", "amt") and self.doc["currency_label"]:
                label = f"{label} ({self.doc['currency_label']})"
            self.text(x + wdt - 2 if al == "R" else x + 2, y, label, bold=True, align=al)
        return y - h

    def table_rows(self, y, cols, lines):
        step = self.fsize + 3
        for line in lines:
            desc_w = next(wdt for k, x, wdt, al in cols if k == "desc") - 4
            dlines = wrap(line["item_description"], self.font, self.fsize, desc_w)
            line["printed_description_lines"] = dlines
            for k, x, wdt, al in cols:
                if k == "desc":
                    yy = y
                    for part in dlines:
                        self.text(x + 2, yy, part)
                        yy -= step
                else:
                    self.text(x + wdt - 2 if al == "R" else x + 2, y, line["cells"].get(k, ""), align=al)
            y -= step * max(1, len(dlines)) + 2
            self.c.setStrokeColorRGB(0.85, 0.85, 0.85)
            self.c.line(self.m, y + step - 2, self.W - self.m, y + step - 2)
            self.c.setStrokeColorRGB(0, 0, 0)
        return y

    def plain_rows(self, y, lines):
        for line in lines:
            line["printed_description_lines"] = [line["item_description"][i:i + 72]
                                                 for i in range(0, len(line["item_description"]), 72)]
            self.text(self.m, y, f"Item {line['line_no']}:")
            y -= 11
            for part in line["printed_description_lines"]:
                self.text(self.m + 20, y, part)
                y -= 11
            for label, key in (("HSN", "hsn"), ("Category", "cat"), ("Qty", "qty"), ("Unit", "unit"), ("Rate", "rate"),
                               ("Amount", "amt")):
                val = line["cells"].get(key, "")
                self.text(self.m + 20, y, f"{label}: {val}")
                y -= 11
            y -= 4
        return y

    # ------------------------------------------------------------ totals & extras
    def totals(self, y):
        d = self.doc
        x = self.W - self.m
        y -= 4
        for label, value in d["totals"]:
            self.text(x - 110, y, label, bold=label.startswith("Invoice total") or label.startswith("Total"), align="R")
            self.text(x, y, value, align="R", bold=label.startswith("Invoice total"))
            y -= self.fsize + 4
        if self.lay.get("tax_summary"):
            y -= 4
            self.text(self.m, y, "HSN-wise tax summary", bold=True)
            y -= self.fsize + 4
            xs = [self.m, self.m + 70, self.m + 170, self.m + 230]
            for i, h in enumerate(["HSN/SAC", "Taxable value", "GST%", "Tax amount"]):
                self.text(xs[i], y, h, bold=True)
            y -= self.fsize + 3
            for row in d["tax_summary"]:
                for i, v in enumerate(row):
                    self.text(xs[i], y, v)
                y -= self.fsize + 3
        if self.lay.get("words") and d.get("amount_in_words"):
            y -= 4
            for part in wrap(d["amount_in_words"], self.font, self.fsize, self.W - 2 * self.m, 3):
                self.text(self.m, y, part)
                y -= self.fsize + 2
        if self.lay.get("bank"):
            y -= 6
            for line in d["bank_lines"]:
                self.text(self.m, y, line)
                y -= self.fsize + 2
        for note in d.get("notes", []):
            y -= 2
            for part in wrap(note, self.font, self.fsize - 0.5, self.W - 2 * self.m, 3):
                self.text(self.m, y, part, size=self.fsize - 0.5)
                y -= self.fsize + 1
        y -= 8
        self.text(self.W - self.m, y, f"for {d['issuer']['name']} - Authorised Signatory", align="R")
        return y

    # ------------------------------------------------------------ main
    def render(self):
        d = self.doc
        pages = d["pages"]
        total = len(pages)
        cols = self.col_layout() if self.lay["cols"] else None
        for n, page_lines in enumerate(pages, start=1):
            self.page_frame(n, total)
            if n == 1:
                y = self.header()
            else:
                y = self.H - self.m
                self.text(self.m, y, f"{d['title']} {d['invoice_number_printed']} (continued)", bold=True)
                y -= 20
            if cols:
                y = self.table_header(y, cols)
                y = self.table_rows(y, cols, page_lines)
            else:
                y = self.plain_rows(y, page_lines)
            if n < total:
                sub = d["carried_forward"][n - 1]
                self.text(self.W - self.m, y - 4, f"Carried forward: {sub}", align="R", bold=True)
                self.text(self.m, y - 4, "Continued on next page")
            else:
                self.totals(y)
            self.c.showPage()
        self.c.save()
