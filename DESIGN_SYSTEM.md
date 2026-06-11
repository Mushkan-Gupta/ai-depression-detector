# MindEase Design System

## Color Palette

### Primary Colors
```
Purple Gradient: #667eea → #764ba2
- Used for: Buttons, accents, primary actions
- Represents: Trust, calmness, professionalism

Mint Green: #48bb78
- Used for: Success states, positive feedback
- Represents: Growth, healing, positivity
```

### Background Colors
```
Dark Mode:
- Primary BG: #0a0e27 (Deep navy)
- Card BG: rgba(255, 255, 255, 0.08) (Translucent white)
- Glass: rgba(255, 255, 255, 0.1)

Light Mode:
- Primary BG: #f0f4f8 (Soft blue-gray)
- Card BG: rgba(255, 255, 255, 0.9) (Nearly opaque white)
- Glass: rgba(255, 255, 255, 0.7)
```

### Text Colors
```
Dark Mode:
- Primary: #eaeaf0 (Off-white)
- Muted: #718096 (Gray)

Light Mode:
- Primary: #1a202c (Dark blue-gray)
- Muted: #718096 (Gray)
```

### Status Colors
```
Success (Low Risk):
- Background: rgba(72, 187, 120, 0.2)
- Text: #38a169
- Badge: rgba(72, 187, 120, 0.2)

Warning (Moderate Risk):
- Background: rgba(237, 137, 54, 0.2)
- Text: #dd6b20
- Badge: rgba(237, 137, 54, 0.2)

Error (High Risk):
- Background: rgba(245, 101, 101, 0.2)
- Text: #e53e3e
- Badge: rgba(245, 101, 101, 0.2)

Loading:
- Background: rgba(102, 126, 234, 0.1)
- Text: #667eea
- Border: rgba(102, 126, 234, 0.3)
```

## Typography

### Font Family
```
Primary: 'Poppins', sans-serif
- Weights: 300 (Light), 400 (Regular), 600 (Semi-bold)
- Source: Google Fonts
```

### Font Sizes
```
Headers:
- H1: 28px (Main titles)
- H2: 24px (Section titles)
- H3: 22px (Subsection titles)

Body:
- Regular: 15px
- Small: 14px
- Tiny: 13px

Buttons: 16px (Semi-bold)
```

## Spacing

### Padding
```
Large: 40px (Page sections)
Medium: 30px (Cards)
Regular: 20px (Components)
Small: 16px (Inputs)
Tiny: 10px (Buttons)
```

### Margins
```
Section: 40px
Component: 20px
Element: 16px
Small: 10px
```

### Gaps
```
Large: 20px
Medium: 16px
Regular: 12px
Small: 10px
```

## Border Radius

```
Extra Large: 50px (Pills, rounded buttons)
Large: 24px (Cards)
Medium: 16px (Inputs, results)
Regular: 12px (Buttons)
Small: 10px (Small elements)
```

## Shadows

### Elevation Levels
```
Level 1 (Subtle):
box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3)

Level 2 (Medium):
box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1)

Level 3 (High):
box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3)

Hover State:
box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5)
```

## Effects

### Glassmorphism
```css
background: rgba(255, 255, 255, 0.1);
backdrop-filter: blur(20px);
border: 1px solid rgba(255, 255, 255, 0.2);
```

### Gradient Overlay
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### Aurora Effect
```css
background:
  radial-gradient(circle at 20% 30%, #7c3aed55, transparent 40%),
  radial-gradient(circle at 80% 40%, #22d3ee55, transparent 45%),
  radial-gradient(circle at 50% 80%, #34d39955, transparent 40%);
filter: blur(80px);
```

## Animations

### Transitions
```css
Standard: all 0.3s ease
Quick: all 0.2s ease
Slow: all 0.5s ease
```

### Keyframe Animations
```
slideUp: 0.6s ease-out
- Entry animation for cards

floatIn: 0.4s ease-out
- Message appearance

breathe: 5s infinite ease-in-out
- AI orb pulsing

pulse: 1.5s infinite ease-in-out
- Loading state

drift: 20s infinite alternate ease-in-out
- Aurora background movement

backgroundMove: 20s linear infinite
- Pattern animation
```

### Hover Effects
```
Buttons:
- transform: translateY(-2px)
- Enhanced shadow

Cards:
- Subtle scale or glow
- No movement (stability)

Inputs:
- Border color change
- Shadow appearance
```

## Components

### Buttons
```
Primary Button:
- Background: Linear gradient (purple)
- Padding: 16px 32px
- Border-radius: 50px
- Font-weight: 600
- Shadow: Medium elevation
- Hover: Lift + enhanced shadow

Secondary Button:
- Background: Transparent/Glass
- Border: 2px solid accent
- Same padding and radius
```

### Input Fields
```
Standard Input:
- Padding: 16px 20px
- Border: 2px solid rgba(102, 126, 234, 0.2)
- Border-radius: 12px
- Background: #f7fafc (light) / rgba(255,255,255,0.1) (dark)
- Focus: Border color change + shadow ring
```

### Cards
```
Standard Card:
- Padding: 40px
- Border-radius: 24px
- Background: Glassmorphism
- Shadow: High elevation
- Backdrop-filter: blur(10px)
```

### Badges
```
Risk Badge:
- Padding: 8px 16px
- Border-radius: 50px
- Font-weight: 700
- Text-transform: uppercase
- Letter-spacing: 0.5px
- Color-coded by risk level
```

## Responsive Breakpoints

```
Mobile: max-width: 768px
- Reduced padding
- Smaller font sizes
- Stacked layouts
- Adjusted component sizes

Tablet: 769px - 1024px
- Medium padding
- Standard font sizes
- Flexible layouts

Desktop: 1025px+
- Full padding
- Large font sizes
- Multi-column layouts
```

## Accessibility

### Contrast Ratios
```
All text meets WCAG AA standards:
- Normal text: 4.5:1 minimum
- Large text: 3:1 minimum
- Interactive elements: Clear focus states
```

### Focus States
```
All interactive elements have visible focus:
- Outline or shadow ring
- Color change
- Scale or position change
```

### Motion
```
Animations are subtle and purposeful:
- No rapid flashing
- Smooth transitions
- Can be disabled via prefers-reduced-motion
```

## Usage Guidelines

### Do's ✓
- Use consistent spacing throughout
- Maintain color hierarchy
- Apply glassmorphism for depth
- Use smooth transitions
- Keep animations subtle
- Ensure good contrast
- Test on multiple devices

### Don'ts ✗
- Don't mix different shadow styles
- Don't use too many colors
- Don't make animations too fast
- Don't forget hover states
- Don't ignore mobile design
- Don't sacrifice readability for style

## Implementation Example

```css
/* Professional Button */
.btn-primary {
  padding: 16px 32px;
  border-radius: 50px;
  border: none;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

.btn-primary:active {
  transform: translateY(0);
}
```

---

This design system ensures consistency and professionalism across the entire application.
