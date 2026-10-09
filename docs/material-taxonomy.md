# Material Taxonomy

> **Status:** PROPOSED. SYNTHETIC — EPRLens Demo.
> "Relevant to plastic EPR" follows the handbook's statement that only plastic packaging is currently under packaging EPR (p.6–7) — **TBD — official-source verification**.
> **Material is never inferred as a legal classification from image appearance alone.** An image model can suggest a probable material; the declared material comes from the product master or a document and requires user confirmation.

| Code | Display name | Broad family | Plastic EPR relevant (packaging) | Typical synthetic components | Limitations |
|---|---|---|---|---|---|
| `PET` | Polyethylene terephthalate | Plastic | Yes | bottles, jars, preforms | Clear PET vs PET-G vs rPET not distinguished; recycled content tracked separately |
| `HDPE` | High-density polyethylene | Plastic | Yes | bottles, caps, drums | |
| `LDPE` | Low-density polyethylene | Plastic | Yes | shrink wrap, bags, liners | LDPE vs LLDPE often blended in practice |
| `LLDPE` | Linear low-density polyethylene | Plastic | Yes | stretch film, pouches, mailers | |
| `PP` | Polypropylene | Plastic | Yes | caps, labels (BOPP), trays, jars | BOPP labels treated as PP film |
| `PVC` | Polyvinyl chloride | Plastic | Yes | blister packs, shrink sleeves | Category (rigid vs flexible) ambiguous for blisters → flagged |
| `PS` | Polystyrene incl. EPS (thermocol) | Plastic | Yes | EPS protective blocks, cups, trays | Handbook names thermocol/EPS under Cat I |
| `MLP` | Multi-layer / multi-material laminate containing plastic | Plastic-containing composite | Yes | snack pouches, sachets, laminated tubes | Term not in handbook (DS-10); default Cat III; layer composition not modelled |
| `COMPOSTABLE` | Compostable plastic | Plastic (compostable) | Yes | compostable carry bags, mailers | Certification not modelled; category IV per handbook |
| `PAPER` | Paper | Fibre | No (EPR under development per handbook) | labels, wraps, void fill | |
| `CARDBOARD` | Cardboard / corrugated board | Fibre | No (under development) | outer cartons, mono cartons | |
| `GLASS` | Glass | Glass | No (under development) | bottles, jars | |
| `METAL` | Metal (aluminium, tinplate) | Metal | No (under development) | cans, foil lids | Aluminium foil inside MLP counts as part of MLP |
| `BATTERY` | Battery | Battery (separate regime) | No — separate Battery EPR regime | **never a packaging component**; reserved for image-class alignment and multi-role tests | |
| `OTHER` | Other / unknown | Other | Unknown → review | wooden pallets, textiles, mixed | Must be reviewed, never silently zero |

Note: `COMPOSTABLE` is an addition to the brief's candidate list, needed to represent handbook Cat IV. If the owner prefers, it can be folded into `OTHER` with category `CAT_IV` (decision folded into DS-09).

## Validation rules

- `plastic_category` must be `NA` when the material family is not plastic.
- `MLP` defaults to `CAT_III`; `COMPOSTABLE` to `CAT_IV`; `PS` with component form `eps_block` to `CAT_I`.
- `BATTERY` in a packaging component row is itself a validation error.
