---
title: Vedrix Design System
version: "1.0"
description: Design tokens and guidelines for Vedrix UI
license: MIT
author: Vedrix UI Team
---

colors:
  background:
    base: "#020617"
    surface: "rgba(2,6,23,0.75)"
  text:
    primary: "#FFFFFF"
    secondary: "#CBD5E1"
  brand:
    purple:
      500: "#7C3AED"
      600: "#6D28D9"
      700: "#4C1D95"
  surface:
    card: "rgba(255,255,255,0.04)"
    elevated: "rgba(255,255,255,0.08)"
  border:
    default: "rgba(255,255,255,0.15)"
gradients:
  primary: "linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%)"
typography:
  fontFamily:
    body: 'Inter, ui-sans-serif, system-ui'
  fontSizes:
    xs: 12
    sm: 14
    base: 16
    lg: 18
    xl: 28
    xxl: 64
  fontWeights:
    regular: 400
    medium: 500
    semibold: 600
    bold: 700
spacing:
  0: 0
  1: 4
  2: 8
  3: 12
  4: 16
  5: 20
  6: 24
  8: 32
  12: 48
  16: 64
  20: 80
  24: 96
 radii:
  none: 0
  xs: 6
  sm: 8
  md: 12
  lg: 16
  xl: 24
  full: 9999
elevation:
  level1: '0 1px 2px rgba(0,0,0,0.08)'
  level2: '0 4px 16px rgba(0,0,0,0.25)'
  level3: '0 8px 24px rgba(0,0,0,0.34)'
  level4: '0 16px 40px rgba(0,0,0,0.4)'
motion:
  durations:
    fast: 150
    regular: 300
    slow: 600
  easing:
    standard: 'ease-in-out'
---

Design intent and usage notes
- Look and feel: A dark, glassy interface with purple accents. Cards have subtle borders and gentle elevation.
- Token usage: Reference colors.brand.purple.* for primary actions; use colors.background.base for the page body.
- Typography: Use body font as a clean sans-serif; headings should be bold with larger sizes for emphasis.
- Spacing: Use consistent 4px increments; larger sections use elevated surfaces with a soft glassy background.
- Motion: Apply small transitions for hover/focus/state changes to feel responsive, not distracting.
- Accessibility: Ensure good contrast and keyboard focus visibility.
- Roadmap: Extend tokens with more components, icons, and a grid system for scalable layouts.

Usage guidance
- Example: Primary button uses colors.brand.purple.600 with fontSizes.base for base text.
- Apply elevation tokens for panels and modals.
- Keep typography consistent with typography.fontFamily and fontSizes tokens.

If you’d like, provide screenshots and I’ll tune token values to faithfully reproduce the visuals.
