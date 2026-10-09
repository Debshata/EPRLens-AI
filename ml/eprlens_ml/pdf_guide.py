"""docs/EPRLens_ML_to_AWS_Engineer_Guide.pdf — plain-language guide for the AWS engineer.
All values are read from the exported artifacts. SYNTHETIC — EPRLens Demo."""
import json
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from .common import ROOT, read_json

GREEN = colors.HexColor("#1b7f4b")
LIGHT = colors.HexColor("#e8f5ee")
OUT = ROOT / "docs" / "EPRLens_ML_to_AWS_Engineer_Guide.pdf"


def styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=ss["Title"], textColor=GREEN, fontSize=22, leading=26),
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], textColor=GREEN, fontSize=15, spaceBefore=8, spaceAfter=4),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12, spaceBefore=6, spaceAfter=3),
        "p": ParagraphStyle("p", parent=ss["BodyText"], fontSize=10, leading=14, alignment=TA_LEFT),
        "small": ParagraphStyle("s", parent=ss["BodyText"], fontSize=8, leading=10, textColor=colors.grey),
        "code": ParagraphStyle("c", parent=ss["Code"], fontSize=7.2, leading=8.6, backColor=colors.HexColor("#f4f4f4"),
                               borderPadding=4),
        "cell": ParagraphStyle("cell", parent=ss["BodyText"], fontSize=8.5, leading=10.5),
    }


def table(rows, widths, S, header=True):
    data = [[Paragraph(str(c), S["cell"]) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), LIGHT)]
    t.setStyle(TableStyle(st))
    return t


def flow(steps, width=170 * mm, title=None):
    """Vertical box-and-arrow diagram."""
    box_h, gap = 16, 10
    h = len(steps) * (box_h + gap) + (14 if title else 0)
    d = Drawing(width, h)
    y = h - (14 if title else 0)
    if title:
        d.add(String(0, h - 10, title, fontName="Helvetica-Bold", fontSize=9, fillColor=GREEN))
    bw = width * 0.62
    x = (width - bw) / 2
    for i, s in enumerate(steps):
        y -= box_h
        d.add(Rect(x, y, bw, box_h, fillColor=LIGHT, strokeColor=GREEN, strokeWidth=0.8, rx=3, ry=3))
        d.add(String(x + bw / 2, y + 5, s, fontName="Helvetica", fontSize=8.5, textAnchor="middle"))
        if i < len(steps) - 1:
            cx = x + bw / 2
            d.add(Line(cx, y, cx, y - gap + 2, strokeColor=GREEN))
            d.add(Polygon([cx - 3, y - gap + 4, cx + 3, y - gap + 4, cx, y - gap], fillColor=GREEN, strokeColor=GREEN))
        y -= gap
    return d


def architecture(width=170 * mm):
    d = Drawing(width, 95)
    boxes = [("App backend (Vercel)", 0), ("AWS Lambda", 1), ("Amazon S3\nmodels/…/v1/", 2), ("Amazon DynamoDB\nresults", 3)]
    bw, bh = 105, 34
    pos = {0: (0, 50), 1: (165, 50), 2: (330, 78 - 8), 3: (330, 8)}
    for name, i in boxes:
        x, y = pos[i]
        d.add(Rect(x, y, bw, bh, fillColor=LIGHT, strokeColor=GREEN, rx=4, ry=4))
        for k, part in enumerate(name.split("\n")):
            d.add(String(x + bw / 2, y + bh - 13 - k * 11, part, fontName="Helvetica", fontSize=8, textAnchor="middle"))
    arrows = [((105, 67), (165, 67), "JSON request", (135, 71)), ((270, 72), (330, 86), "load model", (292, 88)),
              ((270, 58), (330, 30), "store result", (292, 36))]
    for (x1, y1), (x2, y2), label, (lx, ly) in arrows:
        d.add(Line(x1, y1, x2, y2, strokeColor=GREEN))
        d.add(Polygon([x2, y2, x2 - 5, y2 + 3, x2 - 5, y2 - 3], fillColor=GREEN, strokeColor=GREEN))
        d.add(String(lx, ly, label, fontName="Helvetica", fontSize=6.5, textAnchor="middle"))
    return d


def build(run_dir=None, cfg=None):
    cfg = cfg or {"export": {"forecast_dir": "ml/artifacts/forecast/v1", "anomaly_dir": "ml/artifacts/anomaly/v1"}}
    fdir, adir = ROOT / cfg["export"]["forecast_dir"], ROOT / cfg["export"]["anomaly_dir"]
    fmeta, ameta = read_json(fdir / "model_metadata.json"), read_json(adir / "model_metadata.json")
    fin, fout = read_json(fdir / "sample_input.json"), read_json(fdir / "sample_output.json")
    ain, aout = read_json(adir / "sample_input.json"), read_json(adir / "sample_output.json")
    thr = read_json(adir / "threshold.json")
    aws = read_json(ROOT / "ml" / "evaluation" / "aws_artifact_report.json")
    freq = (fdir / "requirements-lambda.txt").read_text().split()
    areq = (adir / "requirements-lambda.txt").read_text().split()
    S = styles()
    W = 170 * mm
    st = []
    P = lambda t, s="p": st.append(Paragraph(t, S[s]))  # noqa: E731
    H1 = lambda t: st.append(Paragraph(t, S["h1"]))  # noqa: E731
    CODE = lambda t: st.append(Preformatted(t, S["code"]))  # noqa: E731
    SP = lambda h=4: st.append(Spacer(1, h * mm))  # noqa: E731

    st.append(Paragraph("EPRLens AI — ML to AWS Engineer Guide", S["title"]))
    P("How to run the two EPRLens models on <b>AWS Lambda</b>, with files in <b>Amazon S3</b> and results in "
      "<b>Amazon DynamoDB</b>. No SageMaker, ECR, Textract, Bedrock or API Gateway is needed.")
    P("SYNTHETIC — EPRLens Demo. Models were trained on synthetic data. Outputs support review; they are not legal "
      "findings.", "small")
    SP()
    H1("What has the ML team built?")
    P("We have trained <b>two models</b>.")
    P(f"<b>1. Forecast model</b> — takes company/product packaging history and predicts <b>next-month packaging kg</b>. "
      f"It is a {fmeta['model_name']} model saved as <b>{fmeta['model_file']}</b>.")
    P("<b>2. Anomaly model</b> — takes transaction/invoice numbers and identifies unusual records. It is used together "
      "with simple deterministic <b>rules</b>. A record is flagged if any rule fires <b>or</b> the model score is above "
      "the saved threshold.")
    st.append(architecture(W))
    SP(2)

    H1("1. What EPRLens is")
    P("EPRLens AI helps Indian businesses check their packaging and EPR records <i>before</i> formal submission: it "
      "validates records, reconciles invoices, flags mistakes, forecasts packaging volume and runs what-if scenarios. "
      "It is not a CPCB portal and not a compliance guarantee.")
    H1("2. What the ML team has built")
    st.append(table([["Model", "Input", "Output", "Main file"],
                     ["Forecast (forecast-v1)", "Product history: month, packaging_kg (+ units, g/unit)", "forecast_kg for next month", fmeta["model_file"]],
                     ["Anomaly (anomaly-v1)", "One invoice with lines, or one recycling record", "is_anomaly, score, rule findings", "isolation_forest.joblib + rules.py"]],
                    [32 * mm, 55 * mm, 42 * mm, 41 * mm], S))
    H1("3. Files you are receiving")
    tree = ["ml/artifacts/forecast/v1/"] + [f"    {p.name:30s}{p.stat().st_size / 1e6:8.3f} MB" for p in sorted(fdir.iterdir())]
    tree += ["ml/artifacts/anomaly/v1/"] + [f"    {p.name:30s}{p.stat().st_size / 1e6:8.3f} MB" for p in sorted(adir.iterdir())]
    tree += ["ml/aws_examples/", "    lambda_forecast_handler.py", "    lambda_anomaly_handler.py",
             "    test_forecast_local.py", "    test_anomaly_local.py"]
    CODE("\n".join(tree))
    P("Every folder has <b>SHA256SUMS.txt</b>. Check it after copying.")

    H1("4. Forecast model")
    st.append(table([["Item", "What it is"],
                     ["Input", "JSON: company_id, product_id, industry, history (oldest first; last entry = latest month)"],
                     ["Output", "JSON: forecast_kg, target_month, model_version, model_name, status"],
                     ["Model file", f"{fmeta['model_file']} (runs with {fmeta['runtime']})"],
                     ["Preprocessor", "preprocessor.joblib — feature order, industry list, seasonality table"],
                     ["Feature code", "features.py — builds the features from the history. Do not rewrite it."],
                     ["Feature schema", f"feature_schema.json — {len(fmeta['features'])} features in a fixed order"]],
                    [35 * mm, 135 * mm], S))
    H1("5. Anomaly model")
    st.append(table([["Item", "What it is"],
                     ["Input", "One invoice record (header, lines, linked internal record, master data, context) or one recycling record"],
                     ["Output", "is_anomaly, anomaly_score (null for recycling), threshold, ml_flag, rule_findings"],
                     ["Model", "isolation_forest.joblib (scikit-learn Isolation Forest)"],
                     ["Threshold", f"threshold.json — {thr['threshold']:.4f}, chosen on validation data"],
                     ["Rules", "rules.py + rules_config.json — duplicate, missing field, quantity/unit mismatch, master-data checks, recycling checks"],
                     ["Feature code", "features.py — builds the 19 numeric features"]],
                    [35 * mm, 135 * mm], S))

    st.append(PageBreak())
    H1("6. Where to put files in S3")
    st.append(table([["Local folder", "S3 location"],
                     ["ml/artifacts/forecast/v1/", "s3://&lt;model-bucket&gt;/models/forecast/v1/"],
                     ["ml/artifacts/anomaly/v1/", "s3://&lt;model-bucket&gt;/models/anomaly/v1/"]], [70 * mm, 100 * mm], S))
    P("This matches the existing AWS design (private bucket, versioning on, block public access).")
    H1("7. What Lambda should do")
    st.append(KeepTogether([flow(["Receive JSON", "Load artifacts (once per cold start)", "Create features (features.py)",
                                  "Predict", "Return JSON"], W, "FORECAST LAMBDA")]))
    st.append(KeepTogether([flow(["Receive record", "Run deterministic rules (rules.py)", "Create ML features (features.py)",
                                  "Run Isolation Forest", "Apply saved threshold", "Combine results", "Return JSON"], W,
                                 "ANOMALY LAMBDA")]))
    H1("8. Exact files Lambda needs")
    st.append(table([["Lambda", "Files from S3"],
                     ["forecast", f"{fmeta['model_file']}, preprocessor.joblib, features.py, model_metadata.json"],
                     ["anomaly", "isolation_forest.joblib, preprocessor.joblib, threshold.json, rules_config.json, features.py, rules.py, model_metadata.json"]],
                    [30 * mm, 140 * mm], S))
    H1("9. Python packages Lambda needs")
    st.append(table([["Lambda", "Packages (exact versions)", "Local install size*"],
                     ["forecast", ", ".join(freq), f"~{aws['forecast_dependencies_total_mb']} MB"],
                     ["anomaly", ", ".join(areq), f"~{aws['anomaly_dependencies_total_mb']} MB"]],
                    [25 * mm, 105 * mm, 40 * mm], S))
    P("*Measured on the Windows development machine. Build Linux wheels for Lambda (manylinux, x86_64 or aarch64). "
      "Put scikit-learn/scipy/numpy in a Lambda layer. Limits: 50 MB zipped direct upload, 250 MB unzipped.", "small")

    st.append(PageBreak())
    H1("10. Sample forecast request")
    CODE(json.dumps(dict(fin, history=fin["history"][-3:]), indent=1) + "\n(only the last 3 of 13 history months shown)")
    H1("11. Sample forecast response")
    CODE(json.dumps(fout, indent=1))
    H1("12. Sample anomaly request (abbreviated)")
    a_short = json.loads(json.dumps(ain))
    a_short["lines"] = a_short["lines"][:1]
    txt = json.dumps(a_short, indent=1)
    CODE(txt if len(txt) < 3500 else txt[:3500] + "\n…")
    H1("13. Sample anomaly response")
    CODE(json.dumps(aout, indent=1))

    st.append(PageBreak())
    H1("14. How to test locally")
    CODE("python ml/aws_examples/test_forecast_local.py\npython ml/aws_examples/test_anomaly_local.py")
    P("Each script loads the exported files, runs the sample request through the reference handler and checks the "
      "answer equals sample_output.json. Nothing is retrained.")
    H1("15. How to upload models to S3")
    CODE("aws s3 cp ml/artifacts/forecast/v1/ s3://<model-bucket>/models/forecast/v1/ --recursive\n"
         "aws s3 cp ml/artifacts/anomaly/v1/  s3://<model-bucket>/models/anomaly/v1/  --recursive")
    H1("16. How Lambda downloads and loads the model")
    P("Set the environment variable <b>MODEL_BUCKET</b>. On a cold start the handler copies the v1 folder from S3 to "
      "<b>/tmp/models/&lt;model&gt;/v1/</b> and keeps the loaded model in memory for warm calls. The Lambda role needs "
      "only <b>s3:GetObject</b> on <b>models/*</b>.")
    st.append(table([["Measured on the local machine (not AWS)", "Forecast", "Anomaly"],
                     ["Model file size", f"{aws['forecast_model_mb']} MB", f"{aws['anomaly_model_mb']} MB"],
                     ["Load time (fresh process)", f"{aws['measured_local_load_time_ms']['forecast']} ms", f"{aws['measured_local_load_time_ms']['anomaly']} ms"],
                     ["Median call time (warm)", f"{aws['measured_local_inference_time_ms']['forecast']['median']} ms", f"{aws['measured_local_inference_time_ms']['anomaly']['median']} ms"],
                     ["Suggested starting memory", f"{aws['recommended_lambda_memory_mb']['forecast']} MB", f"{aws['recommended_lambda_memory_mb']['anomaly']} MB"]],
                    [70 * mm, 50 * mm, 50 * mm], S))
    H1("17. What goes into DynamoDB")
    st.append(table([["Store", "Example"], ["company_id (partition key)", "COMP_0001"],
                     ["timestamp (sort key)", "2026-10-09T10:00:00Z#forecast"], ["model_version", "forecast-v1 / anomaly-v1"],
                     ["analysis result", "forecast_kg, or is_anomaly + anomaly_score"], ["findings", "rule_findings list"],
                     ["record / product id", "INV_… / PROD_…"]], [60 * mm, 110 * mm], S))
    P("<b>Do not</b> store model files in DynamoDB — they stay in S3.")

    st.append(PageBreak())
    H1("18. Common errors")
    st.append(table([["Error", "Likely cause", "Fix"],
                     ["Missing model file", "Wrong S3 prefix or MODEL_BUCKET", "Check models/&lt;model&gt;/v1/"],
                     ["Wrong feature order", "Files from different versions mixed", "Upload the whole v1 folder; check SHA256SUMS"],
                     ["Missing feature / KeyError", "Request missing a field", "Follow the sample request"],
                     ["Wrong Python dependency version", "Different numpy/onnxruntime/sklearn", "Use the exact pinned versions"],
                     ["S3 AccessDenied", "Role lacks s3:GetObject", "Grant read on models/* only"],
                     ["numpy JSON serialization error", "Returning numpy values", "Handlers convert to plain float/bool"],
                     ["Slow first call", "Cold start loads libraries and model", "Keep the model in a global; size memory"]],
                    [45 * mm, 60 * mm, 65 * mm], S))
    H1("19. How to verify integration")
    P("1) Run both local tests. 2) Deploy each Lambda with the same sample event; compare with sample_output.json. "
      "3) Check the result row in DynamoDB has model_version. 4) Send a bad request (empty history) and confirm "
      "status = error.")
    H1("20. Final checklist")
    for item in ["Both v1 folders uploaded to S3; SHA256SUMS checked", "Layers built for the right architecture with pinned versions",
                 "MODEL_BUCKET set on both Lambdas", "IAM: s3:GetObject on models/*, DynamoDB PutItem on the results table only",
                 "Local tests pass; the same sample passes in Lambda", "Results stored with model_version and timestamp",
                 "UI labels results as synthetic demo and not a compliance determination"]:
        P("☐ " + item)
    SP()
    P(f"Generated from the artifacts on {fmeta['training_timestamp'][:10]} · dataset {fmeta['dataset_sha256'][:16]}… · "
      f"git {str(fmeta['git_commit'])[:10]}", "small")

    OUT.parent.mkdir(parents=True, exist_ok=True)

    def footer(canv, doc):
        canv.saveState()
        canv.setFont("Helvetica", 7)
        canv.setFillColor(colors.grey)
        canv.drawString(20 * mm, 10 * mm, "EPRLens AI — ML to AWS Engineer Guide · SYNTHETIC — EPRLens Demo")
        canv.drawRightString(190 * mm, 10 * mm, f"page {doc.page}")
        canv.restoreState()

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm, title="EPRLens ML to AWS Engineer Guide", author="EPRLens ML team",
                            subject="SYNTHETIC — EPRLens Demo")
    doc.build(st, onFirstPage=footer, onLaterPages=footer)
    return OUT
