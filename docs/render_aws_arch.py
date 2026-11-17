"""Render a PPT-ready AWS Batch architecture PNG."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 900
OUT = Path(__file__).with_name("aws-path-architecture.png")
ASSETS = Path(r"C:\Users\Admin\.cursor\projects\d-HPC-L2\assets\aws-path-architecture.png")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def rounded(draw: ImageDraw.ImageDraw, box, fill, outline, radius=18, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def card(draw, box, title, lines, fill, outline, title_fill, body_fill, note=None):
    rounded(draw, box, fill, outline)
    x, y = box[0] + 18, box[1] + 16
    draw.text((x, y), title, font=font(20, True), fill=title_fill)
    yy = y + 34
    for line in lines:
        draw.text((x, yy), line, font=font(15), fill=body_fill)
        yy += 24
    if note:
        draw.text((x, yy + 4), note, font=font(15, True), fill="#b45309")


def arrow_right(draw, x0, y, x1, label):
    draw.line((x0, y, x1 - 8, y), fill="#64748b", width=3)
    draw.polygon([(x1, y), (x1 - 12, y - 7), (x1 - 12, y + 7)], fill="#64748b")
    if label:
        tw = draw.textlength(label, font=font(13))
        draw.text(((x0 + x1) / 2 - tw / 2, y - 22), label, font=font(13), fill="#64748b")


def arrow_down(draw, x, y0, y1, label):
    draw.line((x, y0, x, y1 - 8), fill="#64748b", width=3)
    draw.polygon([(x, y1), (x - 7, y1 - 12), (x + 7, y1 - 12)], fill="#64748b")
    if label:
        draw.text((x + 10, (y0 + y1) / 2 - 8), label, font=font(13), fill="#64748b")


def arrow_up(draw, x, y0, y1, label):
    # from y0 (lower) to y1 (upper)
    draw.line((x, y0, x, y1 + 8), fill="#64748b", width=3)
    draw.polygon([(x, y1), (x - 7, y1 + 12), (x + 7, y1 + 12)], fill="#64748b")
    if label:
        draw.text((x + 10, (y0 + y1) / 2 - 8), label, font=font(13), fill="#64748b")


def arrow_left(draw, x0, y, x1, label):
    # from x0 (right) to x1 (left)
    draw.line((x0, y, x1 + 8, y), fill="#64748b", width=3)
    draw.polygon([(x1, y), (x1 + 12, y - 7), (x1 + 12, y + 7)], fill="#64748b")
    if label:
        tw = draw.textlength(label, font=font(13))
        draw.text(((x0 + x1) / 2 - tw / 2, y - 22), label, font=font(13), fill="#64748b")


def main():
    img = Image.new("RGB", (W, H), "#ffffff")
    d = ImageDraw.Draw(img)

    d.text((40, 28), "Proposed AWS Batch path", font=font(34, True), fill="#1f2937")
    d.text(
        (40, 72),
        "Source in aws/ and docker/. Designed in SAM. This Batch stack was not deployed. Live demo is a separate EC2 dashboard VM.",
        font=font(15),
        fill="#6b7280",
    )

    # Row 1 cards
    card(
        d,
        (40, 120, 300, 290),
        "1  Amazon API Gateway",
        ["HTTP API", "POST /jobs", "GET /jobs/{job_id}", "aws/template.yaml"],
        "#fff7ed",
        "#fdba74",
        "#9a3412",
        "#7c2d12",
    )
    card(
        d,
        (380, 120, 680, 290),
        "2  AWS Lambda",
        ["python3.12 · handler.py", "256 MB · 30 s", "validate + write S3 + SubmitJob"],
        "#fefce8",
        "#fde047",
        "#854d0e",
        "#713f12",
        note="does NOT run CUDA",
    )
    card(
        d,
        (760, 120, 1040, 270),
        "3  Amazon S3",
        ["jobs/ prefix", "AES256 · 14-day expiry", "job.txt + result.json"],
        "#ecfdf5",
        "#6ee7b7",
        "#065f46",
        "#064e3b",
    )

    # Row 2
    card(
        d,
        (380, 360, 680, 520),
        "4  AWS Batch",
        ["spot queue", "g4dn.xlarge / g5.xlarge", "runs same mc_engine on GPU"],
        "#eff6ff",
        "#93c5fd",
        "#1e3a8a",
        "#1e40af",
    )
    card(
        d,
        (760, 360, 1040, 520),
        "5  Amazon ECR",
        ["docker/Dockerfile", "CUDA image + mc_engine", "pulled by Batch workers"],
        "#f5f3ff",
        "#c4b5fd",
        "#5b21b6",
        "#6b21a8",
    )

    # Row 3
    card(
        d,
        (380, 600, 680, 740),
        "6  Amazon EC2",
        ["Batch GPU hosts only", "spot g4dn / g5"],
        "#f8fafc",
        "#cbd5e1",
        "#334155",
        "#475569",
        note="not the dashboard VM",
    )

    # Foundation
    card(
        d,
        (40, 780, 360, 870),
        "AWS IAM",
        ["Lambda, Batch, EC2 instance roles"],
        "#f1f5f9",
        "#94a3b8",
        "#334155",
        "#475569",
    )
    card(
        d,
        (400, 780, 760, 870),
        "Amazon VPC",
        ["subnets + security groups for Batch"],
        "#f1f5f9",
        "#94a3b8",
        "#334155",
        "#475569",
    )

    # Arrows with correct semantics
    arrow_right(d, 300, 205, 380, "invoke")
    arrow_right(d, 680, 175, 760, "put job.txt")
    arrow_down(d, 480, 290, 360, "SubmitJob / DescribeJobs")
    # Batch -> S3 result write (vertical into bottom of S3 from left side of Batch column)
    arrow_up(d, 700, 360, 270, "write result.json")
    arrow_left(d, 760, 440, 680, "pull image")
    arrow_down(d, 530, 520, 600, "launches GPU hosts")

    # Legend strip
    d.text(
        (800, 820),
        "Flow: API → Lambda → S3 + Batch → ECR image → EC2 GPU hosts → result.json in S3",
        font=font(14),
        fill="#475569",
    )

    img.save(OUT, "PNG")
    ASSETS.parent.mkdir(parents=True, exist_ok=True)
    img.save(ASSETS, "PNG")
    print(OUT)
    print(ASSETS)


if __name__ == "__main__":
    main()
