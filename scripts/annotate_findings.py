"""Annotate a medical image with findings from a MedAI E2E report.

Usage:
    python scripts/annotate_findings.py                       # uses defaults
    python scripts/annotate_findings.py --image <path> --report <path>

Draws bounding boxes (if any) and labels on the image.
All bboxes are clearly marked as MODEL-ESTIMATED — MedGemma is a VLM,
not an object detector, so spatial coordinates are approximate at best.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── Colour palette per severity ────────────────────────────
SEVERITY_COLORS = {
    "critical": (220, 20, 60),    # crimson
    "severe":   (255, 69, 0),     # red-orange
    "moderate": (255, 165, 0),    # orange
    "mild":     (255, 215, 0),    # gold
    "none":     (100, 200, 100),  # green
}

BBOX_WIDTH = 3
LABEL_PADDING = 4
DISCLAIMER_COLOR = (255, 80, 80)


def _load_font(size: int = 16) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a TTF font, fall back to default bitmap font."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def annotate(
    image_path: str | Path,
    findings: list[dict],
    output_path: str | Path | None = None,
    image_source_url: str = "",
) -> Path:
    """Draw findings with bboxes on the image and save to output_path."""
    image_path = Path(image_path)
    if output_path is None:
        output_path = image_path.parent / f"{image_path.stem}_annotated{image_path.suffix}"
    output_path = Path(output_path)

    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    label_font = _load_font(max(14, h // 60))
    small_font = _load_font(max(11, h // 80))
    disclaimer_font = _load_font(max(12, h // 70))

    # ── Draw findings ──────────────────────────────────────
    has_any_bbox = False
    for i, f in enumerate(findings, 1):
        severity = f.get("severity", "none")
        color = SEVERITY_COLORS.get(severity, (200, 200, 200))
        confidence = f.get("confidence", 0)
        finding_text = f.get("finding", "Unknown")
        bbox = f.get("region_bbox")

        # Build label
        conf_pct = f"{confidence * 100:.0f}%"
        label = f"F{i}: {finding_text[:50]} ({conf_pct}, {severity})"

        if bbox and len(bbox) == 4:
            has_any_bbox = True
            x1, y1, x2, y2 = bbox

            # Clamp to image dimensions
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            # Draw dashed-style rectangle (solid with alpha impression)
            for offset in range(BBOX_WIDTH):
                draw.rectangle(
                    [x1 - offset, y1 - offset, x2 + offset, y2 + offset],
                    outline=color,
                )

            # Label background
            text_bbox = draw.textbbox((0, 0), label, font=label_font)
            tw = text_bbox[2] - text_bbox[0]
            th = text_bbox[3] - text_bbox[1]
            label_y = max(0, y1 - th - LABEL_PADDING * 2 - BBOX_WIDTH)
            draw.rectangle(
                [x1, label_y, x1 + tw + LABEL_PADDING * 2, label_y + th + LABEL_PADDING * 2],
                fill=color,
            )
            draw.text(
                (x1 + LABEL_PADDING, label_y + LABEL_PADDING),
                label,
                fill=(0, 0, 0),
                font=label_font,
            )

            # ⚠ model-estimated tag inside the bbox
            est_tag = "⚠ MODEL-ESTIMATED REGION"
            draw.text(
                (x1 + BBOX_WIDTH + 2, y2 - 18),
                est_tag,
                fill=DISCLAIMER_COLOR,
                font=small_font,
            )
        else:
            # No bbox — list as text in bottom-left area
            text_y = h - 40 - (len(findings) - i) * 22
            draw.text((10, text_y), f"• {label}", fill=color, font=label_font)

    # ── Global disclaimer banner at top ────────────────────
    disclaimer_lines = [
        "⚠ AI-GENERATED ANALYSIS — FOR PHYSICIAN REVIEW ONLY",
        "Confidences are model-estimated, NOT calibrated probabilities.",
    ]
    if has_any_bbox:
        disclaimer_lines.append(
            "Bounding boxes are LLM-generated approximations, NOT from an object detector."
        )

    banner_h = len(disclaimer_lines) * 20 + 12
    draw.rectangle([0, 0, w, banner_h], fill=(40, 40, 40))
    for j, line in enumerate(disclaimer_lines):
        draw.text((8, 6 + j * 20), line, fill=DISCLAIMER_COLOR, font=disclaimer_font)

    # ── Source info at bottom ──────────────────────────────
    if image_source_url:
        draw.text(
            (8, h - 18),
            f"Source: {image_source_url[:100]}",
            fill=(180, 180, 180),
            font=small_font,
        )

    img.save(output_path, quality=95)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Annotate medical image with MedAI findings")
    parser.add_argument(
        "--image",
        default=str(Path(__file__).resolve().parent.parent / "backend" / "tests" / "fixtures" / "test_chest_xray.jpg"),
        help="Path to the medical image",
    )
    parser.add_argument(
        "--report",
        default=str(Path(__file__).resolve().parent.parent / "backend" / "tests" / "e2e_report_output.json"),
        help="Path to the E2E report JSON",
    )
    parser.add_argument("--output", default=None, help="Output path for annotated image")
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text())
    findings = report.get("findings", [])

    if not findings:
        print("No findings in report to annotate.")
        return

    out = annotate(
        image_path=args.image,
        findings=findings,
        output_path=args.output,
        image_source_url="ieee8023/covid-chestxray-dataset (CC-BY-NC-SA 4.0)",
    )
    print(f"✅ Annotated image saved to: {out}")
    print(f"   Findings drawn: {len(findings)}")
    for i, f in enumerate(findings, 1):
        bbox_str = f"bbox={f.get('region_bbox')}" if f.get("region_bbox") else "no bbox"
        print(f"   {i}. [{f.get('severity','?')}] {f.get('finding','?')[:60]} ({bbox_str})")


if __name__ == "__main__":
    main()
