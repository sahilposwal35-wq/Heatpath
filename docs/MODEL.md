# HeatPath — Exposure Scoring Model Specification

**Document:** `docs/MODEL.md`  
**Version:** 1.0  
**Status:** Implemented in `backend/app/scoring/model.py` and validated by 32 scoring tests  

---

## 1. Principles of the Model

1. **Explainable Heuristic, Not Opaque ML:** In the absence of ground-truth pedestrian microclimate sensor arrays across Pune, a transparent, bounded heuristic is scientifically honest and auditable.
2. **Normalized Inputs:** Every input feature is normalized into the interval $[0, 1]$, where $0$ represents minimal exposure (e.g., night, cool weather, low UV) and $1$ represents severe exposure (e.g., solar noon, high UV index, extreme heat).
3. **Graceful Degradation:** Missing features do not silently default to false constants. Instead, available weights are dynamically re-normalized, and a data confidence flag (`high`, `medium`, `low`) is computed alongside an explicit list of omitted features.

---

## 2. Segment Exposure Score Formulation

For an individual pedestrian route segment $i$:

$$
S_i = \text{clamp}\left( \frac{\sum_{k \in \mathcal{F}_{\text{avail}}} w_k \cdot f_{i,k}}{\sum_{k \in \mathcal{F}_{\text{avail}}} w_k}, 0, 1 \right)
$$

Where $\mathcal{F}_{\text{avail}}$ denotes the set of available features, and $w_k$ denotes the prototype feature weights:

| Feature $k$ | Default Weight $w_k$ | Description |
|---|---|---|
| `sun` | $0.40$ | Solar elevation and direct radiation proxy $\max(0, \sin(\theta_{\text{elev}}))$ |
| `uv` | $0.35$ | Normalized UV Index: $\min(1.0, \text{UV} / 11.0)$ |
| `weather` | $0.25$ | Normalized apparent temperature: $\text{clamp}((\text{ApparentTemp} - 20) / 25, 0, 1)$ attenuated by cloud cover |

### Normalization Details

1. **Sun Factor ($f_{\text{sun}}$):**
   $$
   f_{\text{sun}} = \begin{cases} 0 & \text{if } \theta_{\text{elev}} \le 0^\circ \text{ (night)} \\ \sin(\theta_{\text{elev}}) & \text{if } \theta_{\text{elev}} > 0^\circ \end{cases}
   $$
2. **UV Factor ($f_{\text{uv}}$):**
   $$
   f_{\text{uv}} = \text{clamp}\left(\frac{\text{UV Index}}{11.0}, 0, 1\right)
   $$
3. **Weather Factor ($f_{\text{weather}}$):**
   Let $T_{\text{norm}} = \text{clamp}\left(\frac{T_{\text{apparent}} - 20}{25}, 0, 1\right)$.
   $$
   f_{\text{weather}} = T_{\text{norm}} \cdot \left(1.0 - 0.5 \cdot \frac{\text{CloudCover}\%}{100}\right)
   $$

---

## 3. Route Aggregation

For a route comprised of segments $i \in \{1, \dots, N\}$, with segment durations $d_i$ (seconds):

### 3.1 Duration-Weighted Average Exposure
$$
\bar{S}_{\text{route}} = \frac{\sum_{i=1}^N d_i \cdot S_i}{\sum_{i=1}^N d_i}
$$

### 3.2 Route Multi-Objective Cost
Routes are ranked according to a multi-objective cost function:

$$
C_{\text{route}} = \alpha \cdot \tilde{T} + \beta \cdot \bar{S}_{\text{route}} + \gamma \cdot \tilde{D}
$$

Where:
- $\tilde{T} = \text{clamp}\left(\frac{\text{Duration}_{\text{min}}}{60}, 0, 1\right)$ is normalized walking time (capped at 60 min).
- $\tilde{D} = \text{clamp}\left(\frac{\text{Distance}_{\text{km}}}{5}, 0, 1\right)$ is normalized walking distance (capped at 5 km).
- Profile weight vectors $(\alpha, \beta, \gamma)$:
  - **Faster profile:** $\alpha = 0.60, \beta = 0.20, \gamma = 0.20$
  - **Balanced profile:** $\alpha = 0.40, \beta = 0.40, \gamma = 0.20$
  - **Lower Exposure profile:** $\alpha = 0.20, \beta = 0.65, \gamma = 0.15$

---

## 4. Estimated Model Score Reduction Formula

When comparing candidate route $R$ against the fastest baseline route $B$:

$$
\Delta \% = 100 \times \frac{\bar{S}_B - \bar{S}_R}{\bar{S}_B}
$$

**Strict UI Display Rules:**
1. If $\bar{S}_B \le 0$ or if only one route exists, $\Delta \%$ is `null` (not displayed).
2. The UI explicitly labels this as **"Estimated reduction in model score"**, never "percentage less heat experienced".

---

## 5. Hand-Calculated Reference Example

### Given Input:
- Departure time: 14:00 IST in Pune.
- Solar elevation: $55.23^\circ \implies \sin(55.23^\circ) \approx 0.8215$.
- Open-Meteo weather: Temperature $28.0^\circ\text{C}$, Apparent $30.5^\circ\text{C}$, UV Index $6.0$, Cloud Cover $20\%$.

### Step-by-Step Calculation:
1. **Feature Normalization:**
   - $f_{\text{sun}} = 0.8215$
   - $f_{\text{uv}} = \frac{6.0}{11.0} \approx 0.5455$
   - $T_{\text{norm}} = \frac{30.5 - 20}{25} = \frac{10.5}{25} = 0.4200$
   - $f_{\text{weather}} = 0.4200 \times (1.0 - 0.5 \times 0.20) = 0.4200 \times 0.90 = 0.3780$

2. **Weighted Segment Score:**
   $$
   S_i = (0.40 \times 0.8215) + (0.35 \times 0.5455) + (0.25 \times 0.3780)
   $$
   $$
   S_i = 0.3286 + 0.1909 + 0.0945 = 0.6140
   $$

3. **Comparison:**
   - Baseline Route $B$: Duration $20$ min, Exposure $0.6140$.
   - Alternative Route $R$: Duration $23$ min, Exposure $0.4800$ (e.g. higher tree shade canopy where available).
   - $\Delta \% = 100 \times \frac{0.6140 - 0.4800}{0.6140} = 100 \times \frac{0.1340}{0.6140} = 21.82\%$ estimated model score reduction.
   - Extra time: $+3.0$ minutes.
