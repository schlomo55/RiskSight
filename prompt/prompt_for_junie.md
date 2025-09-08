# 📌 Final Prompt — Risk Processor Assignment

I need you to implement the **Seenity Backend Assignment** with the following rules, clarifications, and improvements.  

---

## ⚠️ Rules  
1. **Keep it simple**: no over-engineering.  
2. **Open for extension**: design so new rules/categories can be added without rewriting the core engine (SOLID, esp. Open/Closed).  
3. Follow good engineering principles: OOP-first, SOLID, KISS, DRY, separation of concerns.  
4. **Ask before assuming**: if something is unclear, stop and ask.  
5. Code must include proper logging (`general.log`, `error.log`), error handling, and documentation.  
6. All tunables must be **centralized in `config/constants.py`** for easy modification.  

---

## ✅ Requirements  

### Part 1 — RiskProcessor (core package)
- Build a Python package named `risk_processor` (src layout).  
- Expose a `RiskProcessor` class with:  
  - **Constructor** parameters: `weights`, `rules`, `noise_level`, `reject_unknown_weather`, `output_scale`.  
  - `process_record(record: dict) -> dict` → returns both aggregate risk score (0–100) and component scores.  
  - `process_many(records: list[dict]) -> list[dict]`.  
- Pipeline per record:  
  1. Normalize inputs (`crime_index`, `accident_rate`, `socioeconomic_level`, `weather`).  
  2. Weighted sum.  
  3. Apply amplification rules.  
  4. Apply noise (if `noise_level > 0`), else bypass.  
  5. Clamp to [0, 1] internally, then scale to **0–100** for output.  
- Raise clear errors for invalid values (ranges or unknown weather).  

### Part 2 — FastAPI service
- Endpoints:  
  - `POST /process` → accept JSON, return risk score + components.  
  - `POST /process-csv` → accept CSV, process rows concurrently, return downloadable CSV.  
- **Concurrency**: `ThreadPoolExecutor`, bounded (default 8 workers), chunk size ~20k rows.  
- **CSV contract**:  
  - Required input columns: `crime_index, accident_rate, socioeconomic_level, weather` (+ optional `city`).  
  - Output = all inputs +  
    `risk_score, crime_component, accident_component, socioeconomic_component, weather_component, processing_status, error_message`.  
  - On error: keep row, blank scores, mark `processing_status=ERROR`, and set `error_message`.  
- **Error handling**:  
  - JSON → return `400` with `{ "detail": "Unknown weather: Foggy" }`.  
  - CSV → row kept with `error_message="Unknown weather: Foggy"`.  

### Logging
- `logs/general.log` → normal processing, summaries.  
- `logs/error.log` → row-level errors, exceptions.  
- Format: `%(asctime)s | %(levelname)s | %(message)s`.  
- During CSV: log each row error, and at the end log a **summary line**, e.g.:  
  ```
  5 errors out of 10,000 rows processed
  ```

---

## 🔧 Centralized Tunables (`config/constants.py`)
- **Risk engine**  
  - `DEFAULT_WEIGHTS`  
  - `DEFAULT_RULES` (list of dicts, freely add/remove rules)  
  - `WEATHER_CATEGORIES` (dict of category → weight)  
  - `DEFAULT_NOISE_LEVEL`  
  - `OUTPUT_SCALE = 100`  
  - `REJECT_UNKNOWN_WEATHER = True`  
  - Ranges: `CRIME_RANGE=(0,10)`, `ACCIDENT_RANGE=(0,10)`, `SOCIO_RANGE=(1,10)`  

- **CSV**  
  - `CSV_REQUIRED_COLUMNS`  
  - `CSV_OPTIONAL_COLUMNS`  
  - `CSV_CHUNK_SIZE = 20000`  
  - `CSV_MAX_WORKERS = 8`  

- **Logging**  
  - `GENERAL_LOG_PATH`  
  - `ERROR_LOG_PATH`  
  - `LOG_FORMAT`  

Changing these values should be enough to change system behavior.  

---

## 🐳 Docker
- Python 3.12 slim base image.  
- Expose port 8000.  
- Run with `uvicorn risk_processor.main:app --host 0.0.0.0 --port 8000`.  

---

## 🧪 Testing
- Cover main flows:  
  - JSON endpoint (valid + invalid inputs).  
  - CSV endpoint (valid rows + error rows).  
  - Error rows produce blank scores and proper messages.  
  - Logging (row-level + summary).  
  - Deterministic runs with `noise_level=0.0`.  

---

👉 **Your task**:  
1. Propose the full project structure (`src/risk_processor/...`, `tests/`, `docs/`, etc.) with responsibilities per file.  
2. After approval, implement it exactly as specified above.  
