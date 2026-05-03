## 🛠 Script Architecture & Modular Structure

This project follows a modular design to ensure code reusability and clean data processing. Each script has a specific responsibility within the pipeline:

| Script | Responsibility | Role in Pipeline |
| :--- | :--- | :--- |
| `config.py` | **Project Settings** | Centralizes global constants, file paths, API keys, and model parameters. Ensures environment consistency. |
| `remote.py` | **Data Acquisition** | Handles the downloading of raw data from external APIs. Includes caching logic to prevent redundant network requests. |
| `io.py` | **Input/Output & ETL** | Responsible for reading raw files, performing data cleaning (standardizing names, handling nulls), and saving processed tables. |
| `metrics.py` | **Core Logic & Stats** | Contains the reusable mathematical formulas and statistical functions used to calculate transit equity scores and delay burdens. |

---

## ⚙️ How the Modules Interact

1. **Initialization:** All scripts import settings from `config.py` to identify where data is stored.
2. **Ingestion:** `remote.py` fetches the latest MTA and Census data, which is then handed off to `io.py`.
3. **Processing:** `io.py` cleans the data and uses the mathematical engines defined in `metrics.py` to generate analysis-ready tables.
4. **Finalization:** The cleaned and analyzed data is saved back to the disk via `io.py` for visualization.
