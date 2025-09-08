# Risk Processing API

A FastAPI service that transforms raw risk indicators into normalized risk scores with strong validation, error handling, and CSV batch support.

## 📌 Overview

The Risk Processing API evaluates risk from four indicators:

- **Crime Index** (0–10)  
- **Accident Rate** (0–10)  
- **Socioeconomic Level** (1–10, inverted to lower risk at higher levels)  
- **Weather** (Clear, Rainy, Snowy, Stormy, Extreme)

**Processing pipeline**:
1. Normalize all inputs → 0–1 scale  
2. Weighted aggregation (configurable in `constants.py`)  
3. Apply amplification rules (e.g. high crime + severe weather)  
4. Add optional noise (for realism)  
5. Scale final score to 0–100  

Invalid values raise clear errors (e.g. `Unknown weather: Foggy`).

---

## 🚀 Quick Start

### Requirements
- Python 3.12+
- Docker (optional)

### Setup
```bash
cd risk-processor

python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows

pip install -r requirements.txt
```

### Run
```bash
python main.py
# or
uvicorn main:app --reload
```

- Docs: [http://localhost:8000/docs](http://localhost:8000/docs)  
- Redoc: [http://localhost:8000/redoc](http://localhost:8000/redoc) 
- Health: [http://localhost:8000/health](http://localhost:8000/health)

### Docker
```bash
docker build -t risk-processor .
docker run -p 8000:8000 risk-processor
```

---

## 📡 API Endpoints

### `POST /process`
Single risk request.

```json
{
  "city": "New York",
  "crime_index": 7.5,
  "accident_rate": 6.2,
  "socioeconomic_level": 4,
  "weather": "Rainy"
}
```

Response:
```json
{
  "city": "New York",
  "risk_score": 72.45,
  "components": {
    "crime_component": 75.0,
    "accident_component": 62.0,
    "socioeconomic_component": 60.0,
    "weather_component": 50.0
  }
}
```

---

### `POST /process-csv`
Upload CSV with required columns:  
`crime_index, accident_rate, socioeconomic_level, weather` (+ optional `city`).

- Valid rows → risk scores added  
- Invalid rows → kept with `processing_status=ERROR` + `error_message`

---

### `GET /health`
System health check.

### `GET /info`
Current processor configuration (weights, rules, categories).

---

## 🛠️ Configuration

All tunables live in **`config/constants.py`**:
- Component weights  
- Amplification rules  
- Weather categories  
- Ranges & validation  
- Noise level  
- CSV worker/chunk size  
- Log paths  

---

## 📂 Project Structure
```
config/       # Constants
core/         # RiskProcessor + validation
services/     # CSV + logging
api/          # FastAPI routes + response models
tests/        # Unit + integration tests
```

---

## ✨ Notes
- Clean architecture, SOLID/OOP principles  
- Centralized configuration → easy to extend (new rules, categories)  
- Detailed logs (`general.log`, `error.log`) with summaries  
- Robust error handling — clear messages, no stack traces exposed  
