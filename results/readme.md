## 🧪 Statistical Results Output

The primary output for the project's analytical findings is stored in the results directory. This file provides the quantitative evidence needed to evaluate the transit equity hypotheses.

### `hypothesis_results.csv`

**Description:** A final statistical summary table containing one row for each hypothesis test conducted (H1 through H4).

| Column Name | Meaning | Purpose |
| :--- | :--- | :--- |
| `hypothesis` | **ID** | The specific hypothesis identifier (e.g., H1, H2). |
| `statistic` | **Test Statistic** | The primary numerical output from the test (e.g., T-score, Regression Coefficient). |
| `p_value` | **Significance** | Evidence of statistical significance (typically significant if < 0.05). |
| `n` | **Sample Size** | The number of observations (stations, lines, or months) included in the test. |
| `ci_low` | **Lower Bound** | The lower limit of the 95% Confidence Interval. |
| `ci_high` | **Upper Bound** | The upper limit of the 95% Confidence Interval. |

---

### 💡 How to Interpret the Results
* **Significance:** If the `p_value` is less than **0.05**, we reject the null hypothesis, suggesting a statistically significant relationship between neighborhood demographics and transit quality.
* **Directionality:** A positive or negative `statistic` indicates the direction of the relationship (e.g., whether delays increase or decrease as income changes).
* **Reliability:** The `n` (sample size) and confidence intervals (`ci_low`/`ci_high`) indicate the robustness and precision of the findings.
