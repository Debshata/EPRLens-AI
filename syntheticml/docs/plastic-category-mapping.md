# Plastic Packaging Category Mapping

> **Status:** PROPOSED. SYNTHETIC — EPRLens Demo.
> Source: handbook Appendix, "Categories of plastic packaging" (p.52), and the registration/compliance sections that use the categories (p.15, p.22, p.41, p.43). Nothing else is added from memory. The definitions themselves are **TBD — official-source verification**.

| Internal code | Handbook name | Definition as supported by handbook | Examples given by handbook | Synthetic-data usage | Uncertainty / TBD |
|---|---|---|---|---|---|
| `CAT_I` | Category I | Rigid plastic packaging and thermocol (expanded polystyrene) | thermocol / EPS (p.52). Bottles appear only as generic examples of plastic packaging (p.5, p.8, p.11), not explicitly as Cat I | Rigid forms: bottles, jars, caps, trays, drums, EPS blocks (declared by form, DS-09) | Whether caps, preforms or thermoformed blisters are "rigid" is **not stated** |
| `CAT_II` | Category II | Flexible plastic packaging incl. single- or multi-layer plastic, sheets, covers, carry bags, sachets and pouches | sheets, covers, carry bags, sachets, pouches (p.52) | Films, shrink/stretch wrap, labels (film), bags, mailers, single-polymer pouches | "Multi-layer plastic" (all-plastic layers) is Cat II; labels as packaging is an assumption |
| `CAT_III` | Category III | Multi-material plastic packaging with ≥ 1 plastic layer and ≥ 1 non-plastic layer | none beyond definition | `MLP` laminates (plastic + aluminium foil/paper): snack pouches, sachets with foil, laminated tubes | Boundary with Cat II for metallised films is **not stated** → flagged ambiguous |
| `CAT_IV` | Category IV | Compostable plastic packaging and carry bags | carry bags (p.52) | `COMPOSTABLE` mailers and carry bags (small share) | Certification requirements **not stated** |
| `NA` | — | Not plastic packaging (paper, cardboard, glass, metal) | — | Non-plastic components | Future regimes (p.7) |
| `UNKNOWN` | — | Category not determinable from available evidence | — | Ambiguous components (`category_confidence="ambiguous"`) and AN06 missing-field tests | Must surface for review; never defaulted |

## How the handbook uses categories (relevant to data design)

- Registration requires a category-wise breakdown of plastic usage, illustrated as "Cat I 40 %, Cat II 30 %" (p.22).
- Targets are category-wise and computed by the portal from historical data (p.22).
- An invoice containing several categories is reported once per category (p.41) → invoice lines carry a category; multi-category invoices (IT09) exist.
- Category misclassification causes targets on the wrong category (p.15) → AN04.

## Synthetic assignment (DS-09 A — approved as a *modelling convention only*)

`synthetic_category` on a component is set by `component_form` (non-plastic materials always get `NA`, e.g. a metal crown cap). This is **not** an official legal classification. Each row also stores `category_basis = "synthetic_convention_by_form"`, `category_confidence` and `legal_verification_status = "TBD"`. The handbook names EPS/thermocol (Cat I), carry bags, sachets and pouches (Cat II) as examples, but no mapping in this table has been verified against an official source. The handbook does not use the term "MLP"; MLP → `CAT_III` is a configurable synthetic default (DS-10).

| component_form | Category | category_confidence |
|---|---|---|
| bottle, jar, cap, closure, tray, drum, tub, preform | CAT_I | declared |
| eps_block | CAT_I | declared (handbook-named) |
| blister | CAT_I | **ambiguous** |
| film, shrink_wrap, stretch_wrap, label_film, bag, mailer, liner, pouch_mono, sachet_mono | CAT_II | declared |
| pouch_laminate, sachet_laminate, laminated_tube | CAT_III | declared |
| compostable_bag, compostable_mailer | CAT_IV | declared |
| carton, box, paper_label, glass_bottle, can | NA | declared |

Every row: `category_basis = "synthetic_convention_by_form"`, `legal_verification_status = "TBD"`. Not a legal classification.
