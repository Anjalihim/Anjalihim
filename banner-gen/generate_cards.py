import xml.sax.saxutils as sax


def esc(text: str) -> str:
    return sax.escape(text)


def wrap_lines(text: str, max_chars: int = 88) -> list[str]:
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if len(cand) <= max_chars:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_card_svg(
    width: int,
    height: int,
    theme: str,
    tag_label: str,
    title: str,
    subtitle: str,
    pills: list[str],
    bullets: list[str],
    accent_hex: str = "#10B981",
) -> str:
    is_dark = theme == "dark"
    card_bg = "#0F172A" if is_dark else "#FFFFFF"
    border = "#22D3EE" if is_dark else "#0891B2"
    title_col = "#F8FAFC" if is_dark else "#0F172A"
    sub_col = "#A78BFA" if is_dark else "#7C3AED"
    body_col = "#CBD5E1" if is_dark else "#334155"
    pill_bg = "#1E293B" if is_dark else "#EEF2FF"
    pill_fg = "#22D3EE" if is_dark else "#0891B2"

    pills_svg = []
    px = 28
    py = 96
    for p in pills:
        pw = len(p) * 7.6 + 20
        if px + pw > width - 28:
            break
        pills_svg.append(
            f'<rect x="{px:.1f}" y="{py}" width="{pw:.1f}" height="24" rx="12" '
            f'fill="{pill_bg}" stroke="{border}" stroke-opacity="0.45" />'
            f'<text x="{px + pw / 2:.1f}" y="{py + 16}" text-anchor="middle" '
            f'font-size="12" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" fill="{pill_fg}">{esc(p)}</text>'
        )
        px += pw + 8

    body_svg = []
    cur_y = 146 if pills else 114
    for idx, b in enumerate(bullets):
        wrapped = wrap_lines(b, max_chars=92)
        delay = round(0.15 + idx * 0.14, 2)
        for l_idx, line in enumerate(wrapped):
            prefix = "• " if l_idx == 0 else "  "
            col = title_col if l_idx == 0 and not pills else body_col
            body_svg.append(
                f'<text x="28" y="{cur_y}" font-size="14" '
                f'font-family="ui-sans-serif, system-ui, -apple-system, sans-serif" fill="{col}" opacity="0">'
                f'<animate attributeName="opacity" from="0" to="1" begin="{delay}s" dur="0.45s" fill="freeze" />'
                f'{esc(prefix + line)}'
                f"</text>"
            )
            cur_y += 22
        cur_y += 6

    final_h = max(height, cur_y + 20)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{final_h}" viewBox="0 0 {width} {final_h}">
  <rect x="2" y="2" width="{width - 4}" height="{final_h - 4}" rx="14" fill="{card_bg}" stroke="{border}" stroke-width="1.6" stroke-opacity="0.75">
    <animate attributeName="stroke-opacity" values="0.45;1;0.45" dur="3.6s" repeatCount="indefinite" />
  </rect>

  <rect x="2" y="14" width="5" height="{final_h - 28}" rx="2.5" fill="{accent_hex}">
    <animate attributeName="opacity" values="0.65;1;0.65" dur="2.8s" repeatCount="indefinite" />
  </rect>

  <circle cx="34" cy="34" r="4.5" fill="{accent_hex}">
    <animate attributeName="r" values="3.5;5.5;3.5" dur="2s" repeatCount="indefinite" />
  </circle>
  <text x="46" y="39" font-size="12" font-weight="600" letter-spacing="1.1"
        font-family="ui-monospace, SFMono-Regular, Menlo, monospace" fill="{accent_hex}">{esc(tag_label)}</text>

  <text x="28" y="66" font-size="19" font-weight="700"
        font-family="ui-sans-serif, system-ui, -apple-system, sans-serif" fill="{title_col}">{esc(title)}</text>

  <text x="28" y="86" font-size="13"
        font-family="ui-monospace, SFMono-Regular, Menlo, monospace" fill="{sub_col}">{esc(subtitle)}</text>

  {"".join(pills_svg)}
  {"".join(body_svg)}
</svg>
'''


def main() -> None:
    files: dict[str, str] = {}

    # Intro Card
    intro_title = "Hi there, I'm Anjali Kumari"
    intro_sub = "Full Stack Developer • Software Development Engineer"
    intro_pills = ["Patna, India", "B.S. CS • IIT Patna (8.56/10.0)"]
    intro_bullets = [
        "Patna, India | B.S. in Computer Science, IIT Patna (CPI: 8.56/10.0).",
        "Full Stack Web Developer and Computer Science undergraduate at IIT Patna with hands-on experience in the MERN stack (MongoDB, Express.js, React.js, Node.js), Next.js, and TypeScript.",
        "Skilled in designing RESTful APIs, building real-time WebSocket applications, optimizing web performance, and developing data pipelines & BI dashboards with Python, SQL, and Power BI.",
    ]
    files["intro-dark.svg"] = make_card_svg(
        860, 255, "dark", "INTRODUCTION", intro_title, intro_sub, intro_pills, intro_bullets, "#22D3EE"
    )
    files["intro-light.svg"] = make_card_svg(
        860, 255, "light", "INTRODUCTION", intro_title, intro_sub, intro_pills, intro_bullets, "#0891B2"
    )

    # Experience
    exp_title = "Data Analyst Intern — GUVI - HCL Technologies"
    exp_sub = "Jun 2025 – Aug 2025 | Remote"
    exp_bullets = [
        "Engineered optimized SQL queries and Python scripts to clean and analyze 10,000+ raw data entries with 99% data integrity.",
        "Built 5+ interactive Power BI dashboards, reducing executive reporting timelines by 25%.",
        "Developed automated ETL pipelines using Pandas and NumPy for structured schema loading.",
    ]
    files["experience-dark.svg"] = make_card_svg(
        860, 235, "dark", "EXPERIENCE", exp_title, exp_sub, [], exp_bullets, "#10B981"
    )
    files["experience-light.svg"] = make_card_svg(
        860, 235, "light", "EXPERIENCE", exp_title, exp_sub, [], exp_bullets, "#059669"
    )

    # Featured Projects
    projects = [
        {
            "slug": "ecommerce",
            "title": "E-Commerce Web Application",
            "sub": "Featured Full-Stack Project",
            "pills": ["React.js", "Node.js", "Express.js", "MongoDB", "Stripe API", "JWT"],
            "bullets": [
                "Full-stack e-commerce platform with JWT authentication, cart persistence, Stripe payments, 12+ REST APIs, and optimized MongoDB indexing (35% lower search latency).",
            ],
            "dark_accent": "#A78BFA",
            "light_accent": "#7C3AED",
        },
        {
            "slug": "chat",
            "title": "Real-Time Chat Application",
            "sub": "Featured Full-Stack Project",
            "pills": ["React.js", "Node.js", "Express.js", "MongoDB", "WebSockets"],
            "bullets": [
                "Real-time messaging application with instant event delivery, room/user state handling, and persistent message history backed by MongoDB.",
            ],
            "dark_accent": "#22D3EE",
            "light_accent": "#0891B2",
        },
        {
            "slug": "portfolio",
            "title": "Personal Portfolio Website",
            "sub": "Featured Web Project",
            "pills": ["React.js", "Next.js", "TypeScript", "Tailwind CSS"],
            "bullets": [
                "Responsive developer portfolio showcasing full-stack web applications, data analytics work, and clean modern UI architecture.",
            ],
            "dark_accent": "#10B981",
            "light_accent": "#059669",
        },
        {
            "slug": "tasks",
            "title": "Task Management Application",
            "sub": "Featured Full-Stack Project",
            "pills": ["React.js", "Node.js", "Express.js", "MongoDB", "Tailwind CSS"],
            "bullets": [
                "Full-stack productivity and workflow application supporting task creation, status tracking, filtering, and RESTful CRUD operations.",
            ],
            "dark_accent": "#A78BFA",
            "light_accent": "#7C3AED",
        },
    ]

    for p in projects:
        slug = p["slug"]
        files[f"project-{slug}-dark.svg"] = make_card_svg(
            860, 215, "dark", "FEATURED PROJECT", p["title"], p["sub"], p["pills"], p["bullets"], p["dark_accent"]
        )
        files[f"project-{slug}-light.svg"] = make_card_svg(
            860, 215, "light", "FEATURED PROJECT", p["title"], p["sub"], p["pills"], p["bullets"], p["light_accent"]
        )

    # Tools & Technologies
    tools_title = "Tools & Technologies"
    tools_sub = "Full-Stack Development, Data Analytics & Developer Workflow"
    tools_pills = ["React.js", "Next.js", "TypeScript", "Node.js", "MongoDB", "Python", "Power BI"]
    tools_bullets = [
        "Frontend & Full-Stack: JavaScript, TypeScript, HTML5, CSS3, Tailwind CSS, React.js, Next.js, Node.js, Express.js, MongoDB.",
        "Data & Analytics: Python, Pandas, NumPy, SQL, Power BI.",
        "Developer Tools: Git, GitHub, VS Code.",
    ]
    files["tools-dark.svg"] = make_card_svg(
        860, 245, "dark", "TOOLS & STACK", tools_title, tools_sub, tools_pills, tools_bullets, "#22D3EE"
    )
    files["tools-light.svg"] = make_card_svg(
        860, 245, "light", "TOOLS & STACK", tools_title, tools_sub, tools_pills, tools_bullets, "#0891B2"
    )

    # Certifications
    cert_title = "Certifications"
    cert_sub = "Verified Training & Skill Credentials"
    cert_bullets = [
        "Data Analytics & Web Development — GUVI - HCL Technologies.",
        "Data Analytics, Power BI & Web Development — WsCube Tech.",
    ]
    files["certifications-dark.svg"] = make_card_svg(
        860, 210, "dark", "CERTIFICATIONS", cert_title, cert_sub, [], cert_bullets, "#10B981"
    )
    files["certifications-light.svg"] = make_card_svg(
        860, 210, "light", "CERTIFICATIONS", cert_title, cert_sub, [], cert_bullets, "#059669"
    )

    for fname, content in files.items():
        with open(fname, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Generated {fname}")


if __name__ == "__main__":
    main()