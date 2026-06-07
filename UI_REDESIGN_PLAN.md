# STEWARD UI Redesign — Design Plan

## Design Direction: "Warm Intelligence"

Inspired by claude.ai's aesthetic — warm, refined, humanist. Away from the cold blue-gray of the
current build. The goal is a UI that feels like a premium personal tool, not a generic admin panel.

---

## Files to change (in order)

1. `src/ui/static/style.css` — full rewrite (the main work)
2. `src/ui/templates/base.html` — sidebar logo, nav refinements
3. `src/ui/templates/ask.html` — proper chat bubble UI (user right / Claude left)
4. `src/ui/templates/index.html` — richer stat cards with gradient accent tops

---

## 1. New Design Token System

Replace the current cold blue-gray palette with a warm, sophisticated one.

```css
:root {
  /* Backgrounds — warm off-white, not cold gray */
  --bg:           #F7F6F3;   /* warm cream, not #f4f6f9 */
  --surface:      #FFFFFF;
  --surface-2:    #FAFAF8;   /* warm, not blue-tinted */

  /* Borders — warm, not cold */
  --border:       #E8E4DD;
  --border-light: #F0EDE8;

  /* Accent — keep blue but shift to indigo for more "AI" feel */
  --accent:       #5B5BD6;   /* indigo-ish, modern */
  --accent-dark:  #4747C2;
  --accent-light: #EFEFFD;
  --accent-rgb:   91, 91, 214;

  /* Text — warm black, not cold slate */
  --text:         #1A1916;
  --text-2:       #57534E;
  --text-3:       #A8A29E;

  /* Sidebar — warm dark, not cold navy */
  --sidebar-bg:    #1C1917;   /* warm near-black */
  --sidebar-text:  #A8A29E;
  --sidebar-active:#FFFFFF;
  --sidebar-hover: #292524;

  /* Status */
  --urgent:        #DC2626;
  --urgent-bg:     #FEF2F2;
  --success:       #16A34A;
  --success-bg:    #F0FDF4;
  --warning:       #D97706;
  --warning-bg:    #FFFBEB;
  --info-bg:       #EFEFFD;

  /* Geometry */
  --radius:        12px;       /* rounder than current 10px */
  --radius-sm:     8px;
  --radius-xs:     5px;

  /* Shadows — warm-tinted, layered */
  --shadow:    0 1px 2px rgba(26,25,22,0.05), 0 2px 6px rgba(26,25,22,0.04);
  --shadow-md: 0 4px 16px rgba(26,25,22,0.08), 0 2px 6px rgba(26,25,22,0.04);
  --shadow-lg: 0 8px 32px rgba(26,25,22,0.12), 0 4px 12px rgba(26,25,22,0.06);

  /* Lift animation (doc cards on hover) */
  --lift: translateY(-2px);
}
```

---

## 2. Sidebar Redesign

Key changes:
- Gradient from `#1C1917` → `#242120` (subtle warm gradient, not flat)
- Brand area: SVG logomark "S" in a rounded square with gradient fill (coral→amber)
- Active nav: left 3px accent border + subtle background, NOT filled background
- Nav items: bigger padding, more breathing room
- Footer: show email status dot if email configured

```html
<!-- Sidebar brand — replace emoji with proper logomark -->
<div class="sidebar-brand">
  <div class="brand-mark">
    <svg viewBox="0 0 32 32" ...>
      <!-- S lettermark in coral-amber gradient -->
    </svg>
  </div>
  <div>
    <div class="brand-name">STEWARD</div>
    <div class="brand-tag">Personal Vault</div>
  </div>
</div>
```

```css
.sidebar {
  background: linear-gradient(180deg, #1C1917 0%, #242120 100%);
  border-right: 1px solid #2C2926;
  /* add subtle right shadow */
  box-shadow: 2px 0 12px rgba(0,0,0,0.15);
}

.sidebar-brand {
  padding: 1.5rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border-bottom: 1px solid #2C2926;
}

.brand-mark {
  width: 34px; height: 34px;
  border-radius: 9px;
  background: linear-gradient(135deg, #F97316 0%, #FBBF24 100%); /* coral → amber */
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(249,115,22,0.35);
}

/* Active nav — left border indicator, not filled background */
.nav-item.active {
  color: #FFFFFF;
  background: rgba(255,255,255,0.06);
  border-left: 3px solid #F97316;  /* coral accent */
  padding-left: calc(1.25rem - 3px);
}
.nav-item:not(.active) {
  border-left: 3px solid transparent;
}
```

---

## 3. Card Elevation System

Three levels:
- Level 1 (default): `--shadow` + `--border`
- Level 2 (hover): `--shadow-md` + `var(--lift)` transform + darker border
- Level 3 (featured/stat): `--shadow-md` + gradient accent top border

```css
/* Base card */
.doc-card {
  border-radius: var(--radius);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}
.doc-card:hover {
  transform: var(--lift);
  box-shadow: var(--shadow-md);
  border-color: #D6D1CA;
}

/* Stat card — gradient top border */
.stat-card {
  position: relative;
  overflow: hidden;
}
.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent) 0%, #8B8BE8 100%);
}
```

---

## 4. Typography Upgrade

```css
/* Import: add DM Sans as secondary for headings */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=DM+Sans:wght@600;700&display=swap');

/* Stat card numbers — use DM Sans, feel weightier */
.stat-value {
  font-family: 'DM Sans', 'Inter', sans-serif;
  font-size: 2.25rem;
  font-weight: 700;
  letter-spacing: -0.04em;
  background: linear-gradient(135deg, var(--text) 0%, var(--text-2) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* Page topbar title */
.topbar-title {
  font-family: 'DM Sans', 'Inter', sans-serif;
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}
```

---

## 5. Button Upgrade

```css
.btn-primary {
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%);
  box-shadow: 0 1px 3px rgba(var(--accent-rgb), 0.3), 0 0 0 1px var(--accent-dark);
  color: #fff;
  border: none;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.btn-primary:hover {
  box-shadow: 0 4px 12px rgba(var(--accent-rgb), 0.35);
  transform: translateY(-1px);
}
.btn-primary:active {
  transform: translateY(0);
}
```

---

## 6. Ask Page — Proper Chat Bubbles

BIGGEST visual improvement. Replace the current Q&A card stack with proper chat bubbles.

```
┌─────────────────────────────────────────────────┐
│                   ┌─────────────────────────┐   │
│                   │ how many files i have?  │◀──┤ user bubble (right, indigo)
│                   └─────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │ S │ You have 14 documents in your vault… │   │◀── Claude bubble (left, white card)
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

```css
.chat-thread {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 1.5rem 0;
}

/* User bubble — right aligned, accent color */
.bubble-user {
  align-self: flex-end;
  max-width: 70%;
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%);
  color: #fff;
  border-radius: 18px 18px 4px 18px;
  padding: 0.75rem 1.1rem;
  font-size: 0.9rem;
  line-height: 1.55;
  box-shadow: 0 2px 8px rgba(var(--accent-rgb), 0.25);
}

/* Claude bubble — left aligned, card style */
.bubble-assistant {
  align-self: flex-start;
  max-width: 80%;
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}
.bubble-avatar {
  width: 30px; height: 30px;
  border-radius: 50%;
  background: linear-gradient(135deg, #F97316, #FBBF24);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.8rem; font-weight: 700; color: #fff;
  flex-shrink: 0; margin-top: 2px;
}
.bubble-content {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px 18px 18px 18px;
  padding: 0.875rem 1.1rem;
  box-shadow: var(--shadow);
  font-size: 0.9rem;
  line-height: 1.7;
  color: var(--text);
}
```

---

## 7. Dashboard Stat Cards — Richer Treatment

```
┌────────────────────────────┐
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │ ← 3px gradient top border
│                            │
│  DOCUMENTS                 │
│  14                        │ ← big DM Sans number
│  in your vault             │
│                        📄  │ ← soft icon bottom-right
└────────────────────────────┘
```

Each stat card gets its own gradient top border color:
- Documents: indigo gradient
- Due soon: orange-red gradient  
- Email: blue gradient
- Processed today: green gradient

---

## 8. Upload Area

```css
.upload-area {
  border: 2px dashed var(--border);
  border-radius: var(--radius);
  padding: 3.5rem 2rem;
  background: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 10px,
    rgba(91,91,214,0.015) 10px,
    rgba(91,91,214,0.015) 20px
  );
  transition: all 0.2s ease;
}
.upload-area:hover, .upload-area.drag-over {
  border-color: var(--accent);
  background: var(--accent-light);
  transform: scale(1.005);
}
```

---

## 9. Doc Type Badge Colors — More Vibrant

```css
.type-warranty  { background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; }
.type-amc       { background: #EDE9FE; color: #4C1D95; border: 1px solid #DDD6FE; }
.type-legal     { background: #FCE7F3; color: #831843; border: 1px solid #FBCFE8; }
.type-service   { background: #D1FAE5; color: #064E3B; border: 1px solid #A7F3D0; }
.type-insurance { background: #DBEAFE; color: #1E3A5F; border: 1px solid #BFDBFE; }
.type-receipt   { background: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; }
.type-other     { background: #F5F5F4; color: #57534E; border: 1px solid #E7E5E4; }
```

---

## Execution Order (next session)

1. **style.css** — full rewrite with all the above (biggest file, do first)
2. **base.html** — sidebar logo SVG + nav border-left pattern + font imports
3. **ask.html** — chat bubble layout replacing current history cards
4. **index.html** — stat card treatment (gradient top borders, icons)

Estimated time: ~25-30 mins of execution

---

## What stays the same

- Layout: sidebar + main-wrap grid (don't touch)
- All functionality (no JS changes)
- All page-level templates EXCEPT ask.html chat bubbles and index.html stat cards
- Architecture and About pages (already written this session)

---

## Quick reference — warm palette swaps

| Old token       | Old value    | New value    | Rationale                |
|-----------------|--------------|--------------|--------------------------|
| `--bg`          | `#F4F6F9`    | `#F7F6F3`    | Warm cream vs cold gray  |
| `--border`      | `#E2E8F0`    | `#E8E4DD`    | Warm vs cold             |
| `--accent`      | `#2563EB`    | `#5B5BD6`    | Indigo, more AI-native   |
| `--sidebar-bg`  | `#0F172A`    | `#1C1917`    | Warm dark vs cold navy   |
| `--text`        | `#0F172A`    | `#1A1916`    | Warm black               |
| `--text-2`      | `#475569`    | `#57534E`    | Warm mid-tone            |
| `--text-3`      | `#94A3B8`    | `#A8A29E`    | Warm muted               |
| `--radius`      | `10px`       | `12px`       | Rounder, friendlier      |
