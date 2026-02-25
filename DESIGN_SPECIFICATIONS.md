# Company Panel - Design Specifications & Layout Guide

## 📐 Layout Structure

```
┌─────────────────────────────────────────────────────┐
│                   RESPONSIVE LAYOUT                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────┐ ┌──────────────────────────────────┐   │
│  │         │ │       PAGE HEADER (TOPBAR)       │   │
│  │ SIDEBAR │ │  [Search] [Menu] [Notifications]│   │
│  │         │ │  [Dark Mode] [Profile Dropdown] │   │
│  │ 270px   │ ├──────────────────────────────────┤   │
│  │         │ │                                  │   │
│  │  [Nav   │ │    MAIN CONTENT AREA             │   │
│  │   Menu] │ │                                  │   │
│  │         │ │  [Page Hero Section]             │   │
│  │         │ │  [Metrics Card Grid]             │   │
│  │         │ │  [Content Sections]              │   │
│  │         │ │                                  │   │
│  └─────────┘ └──────────────────────────────────┘   │
│                                                      │
└─────────────────────────────────────────────────────┘

Mobile View (< 900px):
┌────────────────┐
│ ☰ [Search] ... │ ← Toggle sidebar drawer
├────────────────┤
│ SIDEBAR DRAWER │ ← Slides from left with overlay
│  (Overlay)     │
└────────────────┘
```

---

## 🎨 Color Palette

### Primary Colors
```
Sidebar Gradient:
  Starting: #1e40af (Royal Blue)
  Middle:   #1e3a8a (Darker Blue)
  Ending:   #164e63 (Teal)

Transition: 180deg gradient (top to bottom)
Shadow: rgba(30, 64, 175, 0.5)
```

### Accent Colors (Metric Cards)
```
Gradient-1: #6366f1 → #818cf8 (Indigo)
Gradient-2: #10b981 → #34d399 (Green)
Gradient-3: #f59e0b → #fbbf24 (Amber)
Gradient-4: #ef4444 → #f87171 (Red)
Gradient-5: #0ea5e9 → #38bdf8 (Cyan)
```

### Status Badges
```
Success (Green):  Background: #d1fae5, Color: #047857
Warning (Yellow): Background: #fef3c7, Color: #b45309
Danger (Red):     Background: #fee2e2, Color: #b91c1c
Info (Blue):      Background: #dbeafe, Color: #1d4ed8
Neutral (Gray):   Background: #e5e7eb, Color: #374151
```

### Backgrounds & Borders
```
Main Background: #f4f6fa
Card Background: #ffffff
Hover State:     #f9fafb
Border Color:    #e5e7eb
Text Primary:    #111827
Text Secondary:  #6b7280
Text Muted:      #9ca3af
```

---

## 📏 Sizing & Spacing

### Sidebar
```
Width:           270px (desktop), 86px (collapsed)
Max Height:      100vh
Padding:         20px 12px
Scrollbar Width: 6px
```

### Main Content
```
Margin Left:     270px (desktop), 0 (mobile)
Padding:         20px 25px
```

### Cards
```
Padding:         22px
Border Radius:   18px
Box Shadow:      0 10px 28px rgba(0,0,0,0.06)
Margin Bottom:   20px
```

### Typography
```
Page Title (h2):      32px, font-weight: 700
Section Title (h3):   17px, font-weight: 700
Card Header (h3):     17px, font-weight: 700
Label:                13px, font-weight: 600
Body Text:            13px, font-weight: 400
Eyebrow:              11px, uppercase, letter-spacing: 1px
```

### Spacing Scale
```
4px   - xs
8px   - sm
12px  - md
16px  - lg
20px  - xl
24px  - 2xl
28px  - 3xl
```

---

## 🔘 Component Sizes

### Buttons
```
Primary Button:
  Padding: 8px 14px
  Font-size: 12px
  Border-radius: 8px
  Height: ~36px

Icon Button:
  Width: 36px
  Height: 36px
  Padding: 7px
  Border-radius: 8px
```

### Input Fields
```
Padding: 10px
Border: 1px solid #e5e7eb
Border-radius: 8px
Font-size: 13px
Min-height: 40px
```

### Avatars
```
Company Avatar (sidebar): 52px × 52px
Profile Avatar (header):  36px × 36px
Border-radius: 50%
```

### Pills (Metric Cards)
```
Width: 240px (min)
Height: auto
Padding: 18px 22px
Border-radius: 16px
```

---

## 🎭 Visual Effects

### Hover Effects
```
Card Hover:
  Transform: translateY(-6px)
  Box-shadow: 0 18px 40px rgba(0, 0, 0, 0.18)
  Border-color: rgba(99, 102, 241, 0.3)
  Transition: 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)

Button Hover:
  Transform: translateY(-1px)
  Box-shadow: 0 8px 18px rgba(37, 99, 235, 0.22)

Nav Item Hover:
  Background: rgba(255,255,255,0.18)
  Transform: translateX(6px)
  Icon Transform: scale(1.1)
```

### Animations
```
Smooth Transitions: cubic-bezier(0.34, 1.56, 0.64, 1)
Hover Shine: Linear gradient sweep (500ms)
Pulse Effect: 2s infinite animation on active states
Slide Down: 0.35s animation for accordion
```

### Shadows
```
Small:    0 2px 8px rgba(0,0,0,0.06)
Medium:   0 6px 16px rgba(0,0,0,0.1)
Large:    0 12px 28px rgba(0,0,0,0.14)
Extra:    0 18px 40px rgba(0,0,0,0.18)
```

---

## 🔤 Typography Hierarchy

### H1 - Page Title
- Size: 32px
- Weight: 700
- Color: #111827
- Letter-spacing: -0.5px

### H2 - Section Header
- Size: 24px
- Weight: 700
- Color: #111827

### H3 - Card Header
- Size: 17px
- Weight: 700
- Color: #111827

### H4 - Subsection
- Size: 15px
- Weight: 600
- Color: #374151

### Body Text
- Size: 13px-14px
- Weight: 400-500
- Color: #374151

### Small Text
- Size: 12px
- Weight: 500
- Color: #6b7280

### Eyebrow
- Size: 11px
- Weight: 600
- Text-transform: uppercase
- Letter-spacing: 1px
- Color: #6b7280

---

## 📊 Grid System

### Pill Cards Grid
```
Desktop:    repeat(auto-fit, minmax(240px, 1fr))
Gap:        18px
Margin:     0 0 28px 0
```

### Content Cards Grid
```
Single Col: max-width: 700px
Double Col: 1fr 1fr
Gap:        20px
```

### Table Layout
```
Header Height:    auto
Row Height:       44px (40px padding top/bottom)
Cell Padding:     10px
Border:           1px solid #eef2f7
```

---

## 🎬 Responsive Breakpoints

### Desktop (1024px+)
```
Sidebar: 270px visible
Main content: Full width
Grid columns: 4-5 columns
Font scale: 100%
```

### Tablet (768px - 1024px)
```
Sidebar: 270px visible
Main content: Adjusted
Grid columns: 2-3 columns
Font scale: 95%
```

### Mobile (480px - 768px)
```
Sidebar: Drawer overlay
Main content: Full width
Grid columns: 2 columns
Font scale: 90%
Search: Hidden
```

### Small Mobile (<480px)
```
Sidebar: Full-width drawer
Grid columns: 1 column
Font scale: 85%
Padding: 16px 12px
```

---

## 📦 Component Library

### Cards
- `.card` - Content container
- `.card-header` - Card title area
- `.activity-list` - Activity items
- `.alert-row` - Alert notifications

### Grid Systems
- `.pill-grid` - Metric cards
- `.detail-grid` - Info grid
- `.charts-grid` - Chart containers

### Buttons
- `.btn.primary` - CTA button (blue)
- `.btn.ghost` - Secondary (white/outline)
- `.action-btn` - Table actions
- `.icon-btn` - Icon-only button

### Tables
- `.table` - Data table
- `.table-actions` - Action buttons
- `.table-wrap` - Overflow container

### Text Utilities
- `.eyebrow` - Uppercase label
- `.muted` - Secondary text
- `.label` - Form label

### Status Badges
- `.badge.success` - Green
- `.badge.warning` - Yellow
- `.badge.danger` - Red
- `.badge.info` - Blue

---

## 🖱️ Interaction States

### Button States
```
Normal:   Base style
Hover:   Elevated shadow + slight lift
Active:  Darker background
Disabled: Opacity: 0.5, cursor: not-allowed
Focus:   Box-shadow outline (accessibility)
```

### Input States
```
Default:   Border: #e5e7eb
Focus:     Border: #2563eb, shadow: blue glow
Invalid:   Border: #ef4444
Disabled:  Background: #f3f4f6
```

### Form Elements
```
Checkbox:  12px × 12px
Radio:     16px diameter
Select:    Full width, 40px height
Textarea:  Min-height: 120px
```

---

## ✨ Polish Details

### Sidebar Scroll
```
Width: 6px
Track: transparent
Thumb: rgba(255,255,255,0.35)
Thumb Hover: rgba(255,255,255,0.55)
Border-radius: 3px
```

### Profile Dropdown
```
Position: Absolute bottom-right
Background: #ffffff
Border-radius: 10px
Box-shadow: 0 8px 20px rgba(222, 219, 219, 0.12)
Margin-top: 8px
Min-width: 180px
```

### Search Input
```
Padding: 8px 14px
Placeholder color: #d1d5db
Background: #ffffff
Focus shadow: 0 8px 24px rgba(37, 99, 235, 0.2)
Transform on focus: translateY(-2px)
```

---

## 🎨 CSS Variables Setup (Optional)

```css
:root {
  --color-primary: #1e40af;
  --color-secondary: #06b6d4;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 12px;
  --spacing-lg: 16px;
  --spacing-xl: 20px;
  
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.06);
  --shadow-md: 0 6px 16px rgba(0,0,0,0.1);
  --shadow-lg: 0 12px 28px rgba(0,0,0,0.14);
  
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-full: 999px;
  
  --transition-smooth: cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

---

## 📐 Accessibility

### Focus States
```
Outline: 2px solid #0f172a
Outline-offset: 2px
Applied to: All interactive elements
```

### Color Contrast
```
Text on background: 4.5:1 (WCAG AA)
Border colors: Visible without hue alone
Icon meanings: Text labels provided
```

### Interactive Elements
```
Min size: 44px × 44px
Padding: Sufficient for touch targets
Hover area: Larger than visible element
```

---

## 🖨️ Print Styles

```css
@media print {
  .sidebar { display: none; }
  .main { margin-left: 0; }
  .icon-btn { display: none; }
  .btn.ghost { border: 1px solid #000; }
}
```

---

**Design Spec Version:** 1.0
**Last Updated:** February 17, 2026
**Status:** ✅ Production Ready
