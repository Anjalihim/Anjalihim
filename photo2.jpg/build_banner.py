import math
import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from scipy import ndimage
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

np.random.seed(42)
random.seed(42)

W_GRID, H_GRID = 300, 340


def find_photo() -> str:
    preferred = ["photo2.jpg", "photo_2026-11-20_20-14-04.jpg"]
    for name in preferred:
        if os.path.isfile(name):
            return name
    exts = (".png", ".jpg", ".jpeg", ".webp")
    files = [
        f for f in os.listdir(".")
        if os.path.isfile(f) and f.lower().endswith(exts) and not f.startswith("input_file_")
    ]
    if files:
        return files[0]
    fallback = [f for f in os.listdir(".") if os.path.isfile(f) and f.lower().endswith(exts)]
    if fallback:
        return fallback[0]
    raise FileNotFoundError(
        "Photo nahi mili! Apni photo ko isi folder mein rakhein ya filename check karein."
    )


def crop_and_preprocess(photo_path: str):
    img = Image.open(photo_path).convert("RGB")
    w, h = img.size
    target_ratio = W_GRID / H_GRID

    crop_w = w
    crop_h = min(h, int(round(crop_w / target_ratio)))
    if crop_h > h:
        crop_h = h
        crop_w = min(w, int(round(crop_h * target_ratio)))

    left = max(0, (w - crop_w) // 2)
    top = max(0, min(h - crop_h, int(h * 0.10)))
    cropped = img.crop((left, top, left + crop_w, top + crop_h))
    resized = cropped.resize((W_GRID, H_GRID), Image.Resampling.LANCZOS)

    arr = np.array(resized, dtype=np.float32)
    border = np.concatenate([
        arr[0:10, :, :].reshape(-1, 3),
        arr[:, 0:8, :].reshape(-1, 3),
        arr[:, -8:, :].reshape(-1, 3),
    ], axis=0)
    bg_color = np.median(border, axis=0)
    color_dist = np.linalg.norm(arr - bg_color, axis=2)

    yy, xx = np.mgrid[0:H_GRID, 0:W_GRID]
    subject_zone = ((xx - W_GRID * 0.5) / (W_GRID * 0.36)) ** 2 + (
        (yy - H_GRID * 0.58) / (H_GRID * 0.44)
    ) ** 2
    fg_mask = (color_dist > 28.0) | (subject_zone < 0.72)
    fg_mask = fg_mask & ~((yy < 40) & ((xx < 50) | (xx > W_GRID - 50)))
    fg_mask = ndimage.binary_closing(fg_mask, structure=np.ones((5, 5)))
    fg_mask = ndimage.binary_fill_holes(fg_mask)

    labeled, num_comp = ndimage.label(fg_mask)
    if num_comp > 0:
        sizes = ndimage.sum(fg_mask, labeled, range(1, num_comp + 1))
        fg_mask = labeled == (int(np.argmax(sizes)) + 1)

    gray = ImageOps.grayscale(resized)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = ImageEnhance.Contrast(gray).enhance(1.3)
    gray = gray.filter(ImageFilter.UnsharpMask(radius=3, percent=140, threshold=3))
    gray_arr = np.array(gray, dtype=np.float32)

    return gray_arr, fg_mask


def dither_serpentine(image_float: np.ndarray, mask=None) -> np.ndarray:
    h_i, w_i = image_float.shape
    buf = image_float.copy()
    out = np.zeros((h_i, w_i), dtype=np.uint8)

    for y in range(h_i):
        even = (y % 2 == 0)
        xs = range(w_i) if even else range(w_i - 1, -1, -1)
        step = 1 if even else -1
        for x in xs:
            if mask is not None and not mask[y, x]:
                buf[y, x] = 0.0
                out[y, x] = 0
                continue
            old_val = buf[y, x]
            new_val = 255.0 if old_val >= 128.0 else 0.0
            out[y, x] = 1 if new_val > 0 else 0
            err = old_val - new_val

            nx = x + step
            if 0 <= nx < w_i:
                buf[y, nx] += err * (7.0 / 16.0)
            if y + 1 < h_i:
                px = x - step
                if 0 <= px < w_i:
                    buf[y + 1, px] += err * (3.0 / 16.0)
                buf[y + 1, x] += err * (5.0 / 16.0)
                if 0 <= nx < w_i:
                    buf[y + 1, nx] += err * (1.0 / 16.0)

    return out


def sample_logo_points(logo_name: str, count: int = 900) -> np.ndarray:
    canvas = Image.new("L", (W_GRID, H_GRID), 0)
    draw = ImageDraw.Draw(canvas)
    cx, cy = W_GRID // 2, H_GRID // 2

    if logo_name == "react":
        draw.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill=255)
        for angle in (0, 60, 120):
            orbit = Image.new("L", (W_GRID, H_GRID), 0)
            od = ImageDraw.Draw(orbit)
            od.ellipse((cx - 115, cy - 42, cx + 115, cy + 42), outline=255, width=10)
            rot = orbit.rotate(angle, center=(cx, cy), resample=Image.Resampling.BILINEAR)
            canvas = Image.fromarray(np.maximum(np.array(canvas), np.array(rot)))
    elif logo_name == "nodejs":
        outer = [
            (cx + 112 * math.cos(math.radians(60 * i - 30)),
             cy + 112 * math.sin(math.radians(60 * i - 30)))
            for i in range(6)
        ]
        inner = [
            (cx + 88 * math.cos(math.radians(60 * i - 30)),
             cy + 88 * math.sin(math.radians(60 * i - 30)))
            for i in range(6)
        ]
        draw.polygon(outer, fill=255)
        draw.polygon(inner, fill=0)
        draw.rectangle((cx - 32, cy - 35, cx - 16, cy + 25), fill=255)
        draw.arc((cx - 58, cy + 2, cx - 16, cy + 42), start=0, end=180, fill=255, width=14)
        draw.arc((cx - 2, cy - 36, cx + 44, cy + 4), start=45, end=270, fill=255, width=14)
        draw.arc((cx - 2, cy - 4, cx + 44, cy + 38), start=225, end=90, fill=255, width=14)
    elif logo_name == "typescript":
        draw.rounded_rectangle((cx - 102, cy - 102, cx + 102, cy + 102), radius=24, fill=255)
        draw.rectangle((cx - 72, cy - 18, cx - 10, cy - 2), fill=0)
        draw.rectangle((cx - 49, cy - 18, cx - 33, cy + 68), fill=0)
        draw.arc((cx + 4, cy - 20, cx + 68, cy + 28), start=40, end=275, fill=0, width=16)
        draw.arc((cx + 4, cy + 18, cx + 68, cy + 70), start=220, end=95, fill=0, width=16)

    ys, xs = np.where(np.array(canvas) > 128)
    coords = np.column_stack([xs, ys]).astype(np.float32)
    step = max(1, len(coords) // (count * 4))
    pool = coords[::step]

    chosen = [pool[0]]
    min_dists = np.linalg.norm(pool - chosen[0], axis=1)
    for _ in range(count - 1):
        idx = int(np.argmax(min_dists))
        chosen.append(pool[idx])
        min_dists = np.minimum(min_dists, np.linalg.norm(pool - pool[idx], axis=1))

    return np.array(chosen, dtype=np.float32)


def generate_svg(dots_mat: np.ndarray, mode: str, trajectories: np.ndarray) -> str:
    is_dark = mode == "dark"
    bg_win = "#0A101F" if is_dark else "#F8FAFC"
    bg_panel = "#0F172A" if is_dark else "#FFFFFF"
    border_col = "#1E293B" if is_dark else "#CBD5E1"
    chrome_col = "#22D3EE" if is_dark else "#0891B2"
    dot_col = "#A78BFA" if is_dark else "#7C3AED"
    accent_col = "#10B981"
    text_muted = "#64748B"
    text_val = "#E2E8F0" if is_dark else "#0F172A"

    pts_react, pts_node, pts_ts = trajectories[0], trajectories[1], trajectories[2]
    centroid = pts_react.mean(axis=0)

    bands = {b: [] for b in range(94)}
    intro_groups = {g: [] for g in range(60)}

    for y in range(H_GRID):
        x = 0
        while x < W_GRID:
            if dots_mat[y, x]:
                start = x
                while x < W_GRID and dots_mat[y, x]:
                    x += 1
                length = x - start
                mid_x = start + length * 0.5
                noisy_x = mid_x + float(np.random.normal(0.0, 4.0))
                noisy_y = y + float(np.random.normal(0.0, 4.0))
                band_id = int((noisy_x * 0.7 + noisy_y * 1.1) % 94)
                intro_id = random.randint(0, 59)
                seg = f"M{start} {y}h{length}"
                bands[band_id].append((seg, mid_x, float(y)))
                intro_groups[intro_id].append(seg)
            else:
                x += 1

    intro_parts = []
    for g in range(60):
        if not intro_groups[g]:
            continue
        d_attr = "".join(intro_groups[g])
        begin_s = round((g / 60.0) * 1.6, 3)
        dur_s = round(3.2 - begin_s, 3)
        intro_parts.append(
            f'<path d="{d_attr}" stroke="{dot_col}" stroke-width="1" fill="none" opacity="0">'
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.15;0.95;1" '
            f'begin="{begin_s}s" dur="{dur_s}s" fill="freeze"/>'
            f"</path>"
        )

    key_times = "0;0.211;0.303;0.880;0.972;1"
    band_parts = []
    for b in range(94):
        items = bands[b]
        if not items:
            continue
        d_attr = "".join(it[0] for it in items)
        bx = float(np.mean([it[1] for it in items]))
        by = float(np.mean([it[2] for it in items]))
        dx = round((float(centroid[0]) - bx) * 0.42, 2)
        dy = round((float(centroid[1]) - by) * 0.42, 2)
        band_parts.append(
            f'<g opacity="0">'
            f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;0.95;1" begin="0s" dur="3.2s" fill="freeze"/>'
            f'<path d="{d_attr}" stroke="{dot_col}" stroke-width="1" fill="none">'
            f'<animate attributeName="opacity" values="1;1;0.06;0.06;1;1" keyTimes="{key_times}" '
            f'begin="3.2s" dur="14.2s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0;0 0;{dx} {dy};{dx} {dy};0 0;0 0" keyTimes="{key_times}" '
            f'begin="3.2s" dur="14.2s" repeatCount="indefinite"/>'
            f"</path></g>"
        )

    t_keys = "0;0.211;0.303;0.444;0.535;0.676;0.768;0.908;1"
    t_opac = "0;0;1;1;1;1;1;1;0"
    trav_parts = []
    for i in range(900):
        x1, y1 = round(float(pts_react[i, 0]), 1), round(float(pts_react[i, 1]), 1)
        x2, y2 = round(float(pts_node[i, 0]), 1), round(float(pts_node[i, 1]), 1)
        x3, y3 = round(float(pts_ts[i, 0]), 1), round(float(pts_ts[i, 1]), 1)
        cx_vals = f"{x1};{x1};{x1};{x1};{x2};{x2};{x3};{x3};{x1}"
        cy_vals = f"{y1};{y1};{y1};{y1};{y2};{y2};{y3};{y3};{y1}"
        trav_parts.append(
            f'<circle r="1.35" fill="{chrome_col}" cx="{x1}" cy="{y1}" opacity="0">'
            f'<animate attributeName="opacity" values="{t_opac}" keyTimes="{t_keys}" '
            f'begin="3.2s" dur="14.2s" repeatCount="indefinite"/>'
            f'<animate attributeName="cx" values="{cx_vals}" keyTimes="{t_keys}" '
            f'begin="3.2s" dur="14.2s" repeatCount="indefinite"/>'
            f'<animate attributeName="cy" values="{cy_vals}" keyTimes="{t_keys}" '
            f'begin="3.2s" dur="14.2s" repeatCount="indefinite"/>'
            f"</circle>"
        )

    rows = [
        ("Subject", "Anjali Kumari"),
        ("Role", "Full-Stack Developer | SDE"),
        ("Origin", "Patna, India"),
        ("Education", "B.S. CS, IIT Patna"),
        ("Status", "Building + Learning + Shipping"),
        ("ToolChain", "VS Code, Git, Postman, Power BI, Docker"),
        ("Core.Lang", "JavaScript, TypeScript, Python, SQL"),
        ("Core.Frontend", "React.js, Next.js, Tailwind CSS, Redux"),
        ("Core.Backend", "Node.js, Express.js, Socket.io, REST APIs"),
        ("Core.Database", "MongoDB, PostgreSQL, Firebase"),
        ("Core.Infra", "Vercel, GitHub Actions, Docker"),
        ("Grid.Portfolio", "coming soon"),
        ("Grid.LinkedIn", "linkedin.com/in/anjalihim"),
        ("Grid.GitHub", "github.com/anjalihim"),
    ]

    info_rows = []
    start_y = 148
    row_step = 25
    total_chars = 66
    for idx, (label, val) in enumerate(rows):
        ry = start_y + idx * row_step
        leaders = "." * max(3, total_chars - len(label) - len(val) - 2)
        info_rows.append(
            f'<text x="478" y="{ry}" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" '
            f'font-size="14" textLength="652" lengthAdjust="spacingAndGlyphs">'
            f'<tspan fill="{chrome_col}" font-weight="600">{label}</tspan>'
            f'<tspan fill="{text_muted}"> {leaders} </tspan>'
            f'<tspan fill="{text_val}">{val}</tspan>'
            f"</text>"
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1180 610" width="1180" height="610" shape-rendering="crispEdges">
  <rect width="1180" height="610" rx="14" fill="{bg_win}" stroke="{border_col}" stroke-width="2"/>
  <rect x="1" y="1" width="1178" height="42" rx="13" fill="{bg_panel}"/>
  <line x1="1" y1="43" x2="1179" y2="43" stroke="{border_col}" stroke-width="1"/>
  <circle cx="24" cy="22" r="6" fill="#EF4444"/>
  <circle cx="44" cy="22" r="6" fill="#F59E0B"/>
  <circle cx="64" cy="22" r="6" fill="#10B981"/>
  <text x="590" y="27" text-anchor="middle" font-family="ui-monospace, monospace" font-size="13" fill="{text_muted}">profile.sh-live</text>

  <rect x="24" y="60" width="414" height="524" rx="10" fill="{bg_panel}" stroke="{border_col}" stroke-width="1.5"/>
  <text x="40" y="82" font-family="ui-monospace, monospace" font-size="13" font-weight="700" fill="{chrome_col}">VISUAL.MAP</text>
  <text x="422" y="82" text-anchor="end" font-family="ui-monospace, monospace" font-size="12" fill="{text_muted}">300x340 // DITHER</text>
  <g transform="translate(36,88) scale(1.30)">
    {"".join(intro_parts)}
    {"".join(band_parts)}
    {"".join(trav_parts)}
  </g>
  <text x="40" y="568" font-family="ui-monospace, monospace" font-size="12" fill="{text_muted}">MORPH: REACT &gt; NODE &gt; TS</text>
  <text x="422" y="568" text-anchor="end" font-family="ui-monospace, monospace" font-size="12" fill="{accent_col}">[ACTIVE]</text>

  <rect x="456" y="60" width="700" height="524" rx="10" fill="{bg_panel}" stroke="{border_col}" stroke-width="1.5"/>
  <text x="478" y="92" font-family="ui-monospace, monospace" font-size="13" font-weight="700" fill="{chrome_col}">SYSTEM.INFO</text>

  <rect x="1076" y="75" width="60" height="22" rx="11" fill="#EF4444" fill-opacity="0.16" stroke="#EF4444" stroke-width="1"/>
  <circle cx="1090" cy="86" r="4" fill="#EF4444">
    <animate attributeName="opacity" values="1;0.25;1" dur="1.4s" repeatCount="indefinite"/>
  </circle>
  <text x="1100" y="90" font-family="ui-monospace, monospace" font-size="12" font-weight="700" fill="#EF4444">LIVE</text>

  <line x1="478" y1="112" x2="1134" y2="112" stroke="{border_col}" stroke-width="1"/>
  {"".join(info_rows)}

  <line x1="478" y1="518" x2="1134" y2="518" stroke="{border_col}" stroke-width="1"/>
  <rect x="478" y="532" width="166" height="32" rx="16" fill="{accent_col}" fill-opacity="0.16" stroke="{accent_col}" stroke-width="1.2"/>
  <text x="561" y="553" text-anchor="middle" font-family="ui-monospace, monospace" font-size="14" font-weight="700" fill="{accent_col}">@anjalihim</text>
  <text x="1134" y="553" text-anchor="end" font-family="ui-monospace, monospace" font-size="12" fill="{text_muted}">STATUS: ONLINE // IIT PATNA</text>
</svg>"""

    filename = f"{mode}.svg"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(svg)
    return filename


def main() -> None:
    photo_path = find_photo()
    print(f"Photo selected: {photo_path}")

    gray_arr, fg_mask = crop_and_preprocess(photo_path)
    dark_dots = dither_serpentine(gray_arr, mask=fg_mask)
    dark_dots[~fg_mask] = 0
    light_dots = dither_serpentine(255.0 - gray_arr, mask=None)

    np.save("dark_dots.npy", dark_dots)
    np.save("light_dots.npy", light_dots)

    pts_react = sample_logo_points("react", 900)
    pts_node = sample_logo_points("nodejs", 900)
    pts_ts = sample_logo_points("typescript", 900)

    _, col_12 = linear_sum_assignment(cdist(pts_react, pts_node, "sqeuclidean"))
    pts_node = pts_node[col_12]
    _, col_23 = linear_sum_assignment(cdist(pts_node, pts_ts, "sqeuclidean"))
    pts_ts = pts_ts[col_23]

    trajectories = np.stack([pts_react, pts_node, pts_ts], axis=0)
    np.save("travellers.npy", trajectories)

    for mode in ("dark", "light"):
        mat = dark_dots if mode == "dark" else light_dots
        out_path = generate_svg(mat, mode, trajectories)
        size_kb = os.path.getsize(out_path) / 1024
        print(f"Created {out_path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()