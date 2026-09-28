# T7 HealthVault — Project Overview

## 1. What this project is

T7 HealthVault is an offline-first community health platform designed for frontline workers such as ASHA workers, ANMs, and PHC teams in India. It brings together four major ideas into one system:

- Offline health record management for families and members
- Clinical early warning analysis using vitals data
- On-device AI support for triage and decision support
- Blockchain-backed trust and patient consent integrity

At a high level, the app helps workers capture patient information, monitor vital signs, assess risk, and create tamper-resistant clinical records without requiring a live internet connection for core workflows.

---

## 2. Why this project matters

The app targets a real challenge in rural and semi-urban healthcare: limited connectivity, low infrastructure, and the need for clinical decision support without expensive centralized systems.

The project combines:

- Flutter for mobile experience
- SQLite for local data persistence
- ONNX-based ML inference for sepsis risk
- NEWS2 and DELTA logic for deterioration warnings
- A Python FastAPI relay to MST blockchain
- Solidity smart contracts to anchor consent and medical integrity proofs
- Multilingual Indian-language support for accessibility

This makes it more than a demo app — it is a healthcare workflow system with privacy-preserving, on-device intelligence and verifiable trust layers.

---

## 3. High-level architecture

The repo is split into three broad layers:

1. Frontend / mobile app
   - Flutter app for ASHA worker workflows
   - Handles login, family management, member records, vitals, AI chat, languages

2. Intelligence and decision support
   - Sepsis inference via ONNX model
   - NEWS2 score engine
   - DELTA trend analysis
   - Optional on-device GGUF LLM

3. Trust and verification layer
   - Python relay backend
   - MST blockchain contract interaction
   - Permissioned consent and record anchoring

The project structure is:

```text
T7-MST-Health-Vault/
├── README.md
├── ARCHITECTURE.md
├── about.md
├── backend/
│   ├── chain.py
│   ├── hasher.py
│   ├── main.py
│   ├── requirements.txt
│   ├── worker_keys.py
│   ├── railway.toml
│   └── render.yaml
├── blockchain/
│   ├── contracts.json
│   ├── hardhat.config.js
│   ├── package.json
│   ├── contracts/
│   │   ├── CareCoin.sol
│   │   ├── ConsentRegistry.sol
│   │   ├── IReg.sol
│   │   ├── RecordAnchor.sol
│   │   ├── StipendVault.sol
│   │   └── WorkerRegistry.sol
│   ├── scripts/
│   │   └── deploy.js
│   └── test/
│       └── healthvault.test.js
├── flutter_app/
│   ├── lib/
│   │   ├── main.dart
│   │   ├── core/
│   │   ├── data/
│   │   ├── models/
│   │   ├── screens/
│   │   ├── services/
│   │   └── widgets/
│   ├── assets/
│   ├── android/
│   ├── ios/
│   ├── linux/
│   ├── macos/
│   ├── windows/
│   └── pubspec.yaml
├── model_pipeline/
│   ├── README.md
│   ├── smoke_test.py
│   ├── train_and_export.py
│   ├── data/
│   └── trained/
└── LICENSE
```

---

## 4. Project modules explained in detail

### 4.1 Root documentation

The root folder contains the high-level project docs:

- README.md: overview, release info, and the product pitch
- ARCHITECTURE.md: structure and engineering design notes
- SECURITY.md: security expectations and design notes
- complete-setup-guide.md: onboarding and setup process

These files act as the project’s technical and operational blueprint.

---

### 4.2 Backend layer

The backend is a Python FastAPI service designed to bridge the mobile app with blockchain transactions.

#### Key file: backend/main.py

This file runs the relay API. It connects to the chain, verifies a canonical hash test vector, and exposes endpoints like:

- POST /register-worker
- POST /consent
- POST /anchor
- POST /visit
- GET /verify/{hash}
- GET /health

This is the bridge between app events and blockchain state.

Example:

```python
@app.post("/register-worker")
async def register_worker(
    req: RegisterWorkerRequest,
    x_admin_secret: str | None = Header(None),
):
    _check_admin(x_admin_secret)
    worker_info = create_worker_account(req.worker_name, req.phone, req.aadhaar_last4)
    worker_address = worker_info["address"]
    cred_hash = worker_info["cred_hash"]

    if chain is None:
        return {
            "worker_address": worker_address,
            "cred_hash": cred_hash,
            "tx_hash": None,
            "warning": "Relay in offline mode — not registered on-chain",
        }

    try:
        tx_hash = chain.register_worker(worker_address, cred_hash)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"On-chain registration failed: {str(e)}")
```

Logic:

- verifies admin auth via X-Admin-Secret
- creates a worker keypair and credential hash
- submits registration to the blockchain
- returns transaction hash for verification

#### Key file: backend/hasher.py

This is one of the critical files in the project because it defines the canonical hashing logic used across backend, Flutter, and the web/verifier side.

```python
VITALS_FIELDS = [
    "hr", "sbp", "dbp", "map", "temp", "spo2", "resp", "age", "recorded_at"
]

def canonical_vitals_json(record: dict) -> str:
    ordered = {}
    for field in VITALS_FIELDS:
        val = record.get(field, "")
        if isinstance(val, float):
            rounded = round(val, 2)
            ordered[field] = int(rounded) if rounded == int(rounded) else rounded
        elif isinstance(val, int):
            ordered[field] = val
        else:
            ordered[field] = str(val) if val is not None else ""
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=True)
```

This ensures that the same record is hashed identically across languages and platforms. It prevents mismatch bugs between Python, Dart, and JS implementations.

#### Key file: backend/chain.py

This acts as the blockchain client wrapper.

```python
class ChainClient:
    def __init__(self):
        rpc_url = os.getenv("MST_RPC_URL", "https://testnetrpc.mstblockchain.com")
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
```

It:

- creates a Web3 connection
- binds to all smart contracts
- signs transactions with the relay account
- handles registration, consent, record anchoring, and stipend payouts

#### Key file: backend/worker_keys.py

This file creates and loads worker wallet accounts. The app uses a custodial or relay-managed setup for ASHA workers rather than fully self-sovereign local wallet storage in the app.

---

### 4.3 Blockchain layer

The blockchain folder contains Solidity contracts that anchor trust and managed incentives.

#### Contract: RecordAnchor.sol

This contract stores an immutable anchor for a canonical clinical record hash.

```solidity
mapping(bytes32 => Anchor) public anchors;

function anchor(bytes32 root, bytes32 aiDigest) external onlyActiveWorker {
    require(root != bytes32(0), "RecordAnchor: empty root");
    require(!anchors[root].exists, "RecordAnchor: already anchored");

    anchors[root] = Anchor({
        anchoredBy: msg.sender,
        anchoredAt: uint64(block.timestamp),
        aiDigest: aiDigest,
        exists: true
    });
}
```

Logic:

- records are canonicalized into a hash
- root hash is stored immutably
- if the patient record is tampered with, the hash mismatch can be checked against on-chain data
- AI digest can also be stored when high-risk output is generated

#### Contract: ConsentRegistry.sol

This handles patient consent for provider access.

```solidity
function grant(
    bytes32 patient,
    address provider,
    uint16 categories,
    uint64 expiry
) external onlyActiveWorker returns (uint256 id) {
    require(provider != address(0), "ConsentRegistry: zero provider");
    require(categories > 0, "ConsentRegistry: no categories");
    require(expiry > block.timestamp, "ConsentRegistry: expiry in past");
```

This keeps actual patient identity off-chain. Only a hash commitment is placed on-chain. That is a privacy-preserving design.

#### Contract: StipendVault.sol

This provides incentivized visit completion logic and token payout to workers.

```solidity
function submitVisit(bytes32 visitKey, uint8 taskType) external {
    require(reg.isActive(msg.sender), "StipendVault: worker not active");
    require(visits[visitKey].worker == address(0), "StipendVault: duplicate visit");
    require(rate[taskType] > 0, "StipendVault: unknown task type");
```

A worker submits a visit key representing a task; hospitals or admin then attest and pay a CARE stipend.

---

### 4.4 Flutter application layer

The app is the primary user-facing system.

#### Entry point: flutter_app/lib/main.dart

The app initializes several services before building the UI:

```dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  initializeDatabase();
  await LanguageService.init();
  await AppUpdateService.init();
  await OnDeviceLLMService.initialize();
  final isFirstRun = await LanguageService.isFirstRun();
  runApp(HealthVaultApp(showFirstRunLanguageSetup: isFirstRun));
}
```

This is the app bootstrap. It does the following:

- initializes SQLite / database layer
- initializes language settings
- initializes app update support
- initializes on-device LLM support
- decides whether to show first-run language onboarding

#### Language layer: flutter_app/lib/services/language_service.dart

This is critical for inclusive healthcare access. The app supports a large set of Indian language codes and downloadable packs.

```dart
static const List<Map<String, String>> supportedLanguages = [
  {'code': 'en', 'name': 'English', 'native': 'English', 'flag': '🌐'},
  {'code': 'hi', 'name': 'Hindi', 'native': 'हिन्दी', 'flag': '🇮🇳'},
  {'code': 'kn', 'name': 'Kannada', 'native': 'ಕನ್ನಡ', 'flag': '🇮🇳'},
  {'code': 'te', 'name': 'Telugu', 'native': 'తెలుగు', 'flag': '🇮🇳'},
  {'code': 'ta', 'name': 'Tamil', 'native': 'தமிழ்', 'flag': '🇮🇳'},
];
```

The service uses SharedPreferences to persist:

- user-selected language
- whether the app has completed first-run setup
- downloaded language packs

#### Local DB: flutter_app/lib/services/local_db_service.dart

This stores all app data locally using SQLite.

```sql
CREATE TABLE families(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  family_head_name TEXT,
  house_number TEXT,
  contact_number TEXT,
  area_id INTEGER
);

CREATE TABLE members(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  family_id INTEGER,
  full_name TEXT,
  age INTEGER,
  gender TEXT,
  relationship_to_head TEXT,
  abha_id TEXT,
  mobile_number TEXT,
  is_pregnant INTEGER DEFAULT 0,
  lmp_date TEXT,
  edd_date TEXT,
  ...
);
```

It manages:

- ASHA worker authentication
- household registration
- member records
- medical vitals history
- area and jurisdiction mapping
- maternal and chronic condition metadata

This is the backbone of the local health record system.

#### Clinical scoring layer: flutter_app/lib/services/news2_delta_service.dart

This service implements the NEWS2 early-warning logic according to clinical scoring rules.

```dart
final rr = (record['respiratory_rate'] as num?)?.toInt();
int rrScore = 0;
if (rr != null) {
  if (rr <= 8) {
    rrScore = 3;
  } else if (rr >= 9 && rr <= 11) {
    rrScore = 1;
  } else if (rr >= 12 && rr <= 20) {
    rrScore = 0;
  } else if (rr >= 21 && rr <= 24) {
    rrScore = 2;
  } else if (rr >= 25) {
    rrScore = 3;
  }
}
```

It computes total NEWS2 score and risk band:

- 0–4: low risk
- 5–6: medium risk
- 7+: high risk

DELTA logic compares current and previous vital readings to spot deterioration trends.

#### Sepsis inference: flutter_app/lib/services/sepsis_inference_service.dart

This is where the ML risk logic lives.

```dart
final featureVector = extraction.featureVector;
final inputOrt = OrtValueTensor.createTensorWithDataList(
  Float32List.fromList(featureVector),
  [1, featureVector.length],
);
final outputs = _session!.run(runOptions, {'vitals_input': inputOrt});
```

This code:

- loads the ONNX model from assets
- converts patient records into a 62-element feature vector
- runs on-device inference
- merges it with emergency thresholds and safety rules

Important logic:

- for each vital channel it computes latest, mean, min, max, std, trend
- it creates clinical emergency indices such as shock index, qSOFA, hypoxemia, hypoglycemia, BP crisis
- if high-risk thresholds are crossed, it automatically raises the risk score

Snippet from the fusion logic:

```dart
if (shockIdx != null && !shockIdx.isNaN && shockIdx >= 1.0) {
  final boost = 0.65 + (shockIdx - 1.0) * 0.25;
  riskScore = math.max(riskScore, boost.clamp(0.65, 0.95));
}

if (qsofa >= 2.0) {
  riskScore = math.max(riskScore, 0.72);
} else if (qsofa >= 1.0) {
  riskScore = math.max(riskScore, 0.35);
}
```

This gives the app a “clinical safety override” layer beyond the raw model output.

#### On-device LLM: flutter_app/lib/services/on_device_llm_service.dart

The app supports an optional GGUF language model for medical queries.

```dart
static const String modelFileName = 'Qwen3-1.7B-Q4_K_M.gguf';
static const String modelDownloadUrl =
    'https://huggingface.co/unsloth/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf';
```

The service can:

- detect if model exists locally
- resume partially downloaded model files
- pause and resume downloads
- manage storage deletion
- show progress and ETA

This is implemented with HTTP Range requests and a temporary .tmp file for fail-safe resumption.

#### Screens and UX flow

The Flutter screen set includes:

- login_screen.dart
- language_setup_screen.dart
- asha_home_screen.dart
- family_detail_screen.dart
- member_detail_screen.dart
- admin_dashboard.dart
- admin_settings_screen.dart
- master_jurisdiction_editor_screen.dart
- state_jurisdiction_detail_screen.dart

The flow is:

1. user logs in as ASHA or admin
2. selects or configures language
3. sees home dashboard
4. adds family and member records
5. records vital signs
6. runs AI/NEWS2 analysis
7. optionally opens the AI clinical chat

---

### 4.5 Machine learning pipeline

The model_pipeline folder is where the sepsis model is trained and exported.

#### File: model_pipeline/README.md

This explains the pipeline:

- uses PhysioNet 2019 ICU data
- extracts vitals-only features
- trains a classifier
- exports to ONNX
- copies model to Flutter assets

#### File: model_pipeline/smoke_test.py

This validates the full data pipeline on a small subset before full training.

#### File: model_pipeline/train_and_export.py

This is the training/export script. It:

- downloads patient data
- aggregates time-series vitals
- builds statistical features
- trains model
- exports ONNX
- validates outputs against scikit-learn

The project is designed for offline inference on a phone, which is why the model is converted to ONNX and packaged into the Flutter app.

---

## 5. End-to-end logic: how the system works

### Step 1 — ASHA worker logs in

The worker opens the app and authenticates with their name and phone number, or an admin logs in with username/password.

The local DB matches the user against SQLite tables.

### Step 2 — Family and member records are created

A family is assigned to a village/area and a person is added to that family.

The application stores:

- household information
- member demographics
- pregnancy status
- chronic conditions
- contact details

### Step 3 — Vitals are recorded

The worker enters values such as:

- pulse rate
- blood pressure
- temperature
- oxygen saturation
- respiratory rate
- blood sugar
- notes

### Step 4 — Clinical decision support runs

The app triggers multiple analysis modules:

- NEWS2: early warning score based on vital ranges
- DELTA: difference from previous readings
- Sepsis inference: machine learning model over vital trajectory stats

The system evaluates both absolute abnormality and trend deterioration.

### Step 5 — Optional AI assistant is used

If the GGUF model is downloaded, the user can ask questions in local language about:

- fever management
- maternal care
- urgent symptoms
- vital interpretation
- counseling guidance

The AI is designed to work offline on-device.

### Step 6 — Consent and record integrity are anchored

The backend computes a canonical hash of vitals and submits it to blockchain via the relay service.

This creates an integrity record that can be audited later.

### Step 7 — Hospital or verifier checks data

A hospital or trusted verifier can query the public endpoints and compare the recomputed hash with the blockchain anchor. If a record was modified after anchoring, it becomes visible.

---

## 6. Why the hashing and blockchain logic matters

The most important integrity design here is not just storing the data on-chain, but storing a deterministic hash of the data. That means:

- raw PII stays local
- only a hash commitment is on-chain
- tampering is detectable
- the hospital can verify a record without reading the entire medical dataset from a public chain

This is a strong privacy- and trust-preserving approach for healthcare data.

---

## 7. Core strengths of the project

- Offline-first design for low-connectivity environments
- Real clinical risk analysis and red-flag logic
- Multilingual support for India’s official languages
- Privacy-aware patient data handling
- On-device AI capabilities
- Blockchain-backed integrity and consent tracking
- Local-first storage with low operational dependence on cloud infrastructure

---

## 8. Potential limitations and future improvements

This is a strong prototype and hackathon-grade system, but there are still future opportunities:

- stronger regulated clinical validation before deployment in real medical workflows
- more formal model calibration and A/B testing
- secure key management and encryption for worker credentials
- better interoperability with public health information systems
- expanding support for more region-specific protocols and maternal care guidelines
- adding proper authentication and RBAC for production-grade deployment

---

## 9. Summary

T7 HealthVault is a full-stack health intelligence project that combines:

- mobile patient/community health workflows
- multilingual access in Indian languages
- offline ML-based sepsis and deterioration detection
- healthcare guidance and prompt-driven AI
- blockchain-based consent and tamper-proof record anchoring

In short, it aims to give state-level and community healthcare workers a privacy-preserving, decision-support platform that works even in low-resource settings.

This project is not just an app — it is a complete healthcare trust architecture for field conditions.

---

## 10. Quick project directory map

```text
backend/           - FastAPI bridge and blockchain relay logic
blockchain/        - Solidity contracts, deployment scripts, test suite
flutter_app/       - mobile app UI and local clinical workflow logic
model_pipeline/    - training and export pipeline for the sepsis model
README.md          - product-level overview
ARCHITECTURE.md    - engineering architecture notes
about.md           - this overview document
```

If you want, this project can be extended into a production-ready clinical system with stronger authentication, encryption, clinician review workflows, and a formal health-data compliance layer.
