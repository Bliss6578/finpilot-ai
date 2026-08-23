# Paymentor AI — Design Direction

## Three Visual Approaches

| Theme Name | Very Brief Intro | Probability |
|---|---|---:|
| Ledger Atelier | A warm editorial interpretation of finance software: precise data surfaces paired with paper-like space and measured ink accents. It makes complex information feel calm and considered. | 0.07 |
| Flight Deck | A high-clarity operational dashboard built around a decisive left rail, horizon-like financial projections, and a single intelligent accent. It should feel like a trusted control room rather than a retrospective report. | 0.03 |
| Soft Circuit | A light, technical system with fine rules, compact panels, and restrained machine-like details. It emphasizes the signal flow from payments to decisions. | 0.09 |

## Chosen Approach — Flight Deck

### Design Movement

**Contemporary financial cockpit**: influenced by highly legible aviation instrumentation, Swiss editorial composition, and the calm operating surfaces of the best modern finance products. The result is precise and confident without becoming a dark “trader terminal” or a futuristic AI interface.

### Core Principles

1. **Decisions before reporting.** Cash risk, forecast direction, and recommended next actions take precedence over historical data.
2. **A composed hierarchy.** Large working surfaces are punctuated by small precision panels, so every page has a clear reading order.
3. **Quiet credibility.** Fine borders, low-elevation surfaces, simple tonal fields, and restrained use of colour communicate reliable financial software.
4. **Data earns colour.** Indigo signals the Paymentor intelligence layer; green, amber, and red only communicate financial state or change.

### Color Philosophy

The working canvas is a cool mist (`#F7F8FA`) that gives white analysis surfaces definition without heaviness. A graphite-black navigation rail creates a stable visual anchor. **Signal Indigo (`#635BFF`)** is Paymentor’s ownable control colour: it appears on the active route, key CTAs, and forecast intelligence. Status hues are intentionally softened and reserved for variance, risk, and health conditions so they retain meaning.

### Layout Paradigm

The application uses a persistent 250px **control rail** and a content workspace that feels like an instrument panel. Pages lead with a broad “situation” band, then move into an asymmetrical sequence of forecast, insight, and supporting evidence. The primary analytic story occupies the larger side; diagnostic cards stack as an adjacent decision column instead of resolving into a uniform card grid.

### Signature Elements

1. **Signal rails:** thin indigo rules and small uppercase labels identify decision-critical panels.
2. **Forecast horizons:** charts use an understated future band and a dashed forecast path to distinguish what happened from what may happen.
3. **Instrument capsules:** compact metric labels, period controls, and state badges use precise pill forms with gentle borders.

### Interaction Philosophy

Interaction should be direct and deliberate. Hovering clarifies affordances with a subtle surface lift and a thin indigo edge; selection states are decisive rather than flashy. Contextual controls route the user along the core journey—from risk, to forecast, to explanation, to scenario—without leaving them stranded.

### Animation

Use transitions only to acknowledge state changes: cards lift 2px over 180ms, drawer and toast entrances use a 240ms ease-out slide with opacity, and chart/tooltips appear with a short fade. Numeric scores can settle into view on first render, but no looping motion is used. All non-essential motion respects reduced-motion preferences.

### Typography System

**Manrope** is used for interface text because its compact, friendly geometry keeps dense financial content readable. **DM Mono** is reserved for currency values, identifiers, and data timestamps to create an instrument-like contrast. Page titles are Manrope 700 at 30–32px; section titles are 18–20px/700; primary money values are DM Mono 700 at 26–32px; metadata is Manrope 12–13px/600 with controlled letter spacing.

### Brand Essence

**Paymentor AI is the decision cockpit for Razorpay businesses that need to see the next financial move before it becomes a problem.**

**Personality:** vigilant, composed, incisive.

### Brand Voice

Paymentor speaks with direct financial clarity: concise, evidence-led, and action-oriented. Headlines identify a financial situation; CTAs make the next decision explicit.

> “Your cash buffer is likely to dip below reserve on Sep 12.”

> “Compare the hiring plan before you commit.”

### Wordmark & Logo

The logo is a compact **pilot beacon**: a precise indigo square with a rising white route line that turns toward a forward dot. The wordmark is deliberately spare, with “Fin” in white and “Pilot” in a softened slate when displayed on the dark rail. The mark is used independently in constrained spaces.

### Signature Brand Color

**Signal Indigo — `#635BFF`**

## Style Decisions

All product pages will reinforce the Flight Deck philosophy: one decision story at a time, crisp operational hierarchy, and a visually obvious distinction between actual performance and Paymentor’s forward-looking intelligence.

- The graphite control rail is persistent on every desktop product route; the top bar is only utility chrome.
- Every page opening states a financial situation or a decision to make, rather than greeting the user or repeating a navigation label.
- Signal Indigo is exclusive to Paymentor intelligence, active navigation, and primary decisions. Operational colours indicate financial state and risk only.

## Validation Notes

The final desktop review confirms that the graphite control rail, pilot beacon, active indigo route state, direct situation-led headers, signal rails, financial instrumentation labels, and forecast-versus-actual chart grammar are visible across the Command Center, Transactions, Cash Flow, and Alerts workspaces. The payment ledger, alert filtering, scenario controls, AI CFO question flow, and financial settings controls use local mock data and provide interactive frontend behaviour while remaining ready to replace with API data later.
