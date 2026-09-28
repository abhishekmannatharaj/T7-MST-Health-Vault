# 🏥 T7 HealthVault — Frontline Worker Zero-PII Audit & MST Blockchain Incentive Protocol

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/b2134f40-8908-481a-8c20-b1a2b4068cb7" />


> **A decentralized trust and automated micro-stipend protocol built for India's frontline healthcare ecosystem (ASHAs & ANMs), pairing offline-first clinical intelligence with sub-second on-chain settlement on MST Blockchain.**

---

## ⚡ Live MST Testnet Verifications

All smart contracts are compiled with Solidity `^0.8.24` and deployed on the **MST Testnet (Cancun EVM)**.

| Component | Detail / Verification Link |
| :--- | :--- |
| **Network Name** | **MST Testnet** |
| **Chain ID** | `91562037` |
| **RPC Endpoint** | `https://testnetrpc.mstblockchain.com` |
| **Explorer** | [testnet.mstscan.com](https://testnet.mstscan.com) |
| **Smart Contract** | `AshaVault.sol` |
| **Deployed Contract Address** | [`0x33Ef1680EcA40d863fc00C460EB9975bbBA12d9f`](https://testnet.mstscan.com/address/0x33Ef1680EcA40d863fc00C460EB9975bbBA12d9f) |
| **Verified Live Transaction** | [`0xdadb4ec25fc13afa95dc1f89927a181ee5c1e6eff1a06c74387fed5290d48de8`](https://testnet.mstscan.com/tx/0xdadb4ec25fc13afa95dc1f89927a181ee5c1e6eff1a06c74387fed5290d48de8) |
| **Disbursement Rate** | `0.50 $MSTC` per verified milestone checkup |

---
<img width="1690" height="866" alt="image" src="https://github.com/user-attachments/assets/5a08ada7-ae8f-4ff7-b962-02133ef32a72" />

<img width="1625" height="826" alt="image" src="https://github.com/user-attachments/assets/529e119d-1746-4413-af60-1b592206a6f5" />

<img width="1877" height="577" alt="image" src="https://github.com/user-attachments/assets/2295a0dc-c410-4638-aa5c-a5190970f9b9" />


## 1. 🔗 MST Blockchain Integration Architecture

### The Problem We Solve On-Chain
In rural public healthcare, Accredited Social Health Activists (ASHAs) face **3 to 6-month bureaucratic delays** to receive routine task stipends (e.g., maternal checkups, polio boosters). Simultaneously, health ministries combat **phantom records and double-claim fraud**. 

Dumping medical charts onto a public chain violates privacy regulations (DPDP Act & HIPAA). **T7 HealthVault decouples private medical data from public cryptographic verification.**

```text
 ┌─────────────────────────────────────────────────────────┐
 │       Frontline Worker Field Entry (Offline App)        │
 │  • Captures vitals, maternal checkup, child vaccine     │
 │  • Stored in LOCAL encrypted SQLite DB (Zero PII leaked)│
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │               FastAPI Canonical Relayer                 │
 │  • Normalizes fields via deterministic JSON serializer  │
 │  • taskHash = keccak256(worker, patientToken, task, ts) │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │         MST Testnet Smart Contract (AshaVault.sol)      │
 │  1. require(!executedTasks[taskHash])  --> Anti-Replay  │
 │  2. executedTasks[taskHash] = true     --> Immutability │
 │  3. worker.call{value: 0.5 ether}("")  --> Auto-Payout  │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │                Public Health Verification               │
 │  • Supervisor audit trail live on testnet.mstscan.com   │
 └─────────────────────────────────────────────────────────┘
```

### Core Blockchain Utilities

1. **Zero-PII Deterministic Hashing (`keccak256`)**:
Instead of writing patient names or vitals on-chain, our backend produces a deterministic 32-byte audit digest:

$$\text{taskHash} = \text{keccak256}(\text{workerAddress}, \text{patientToken}, \text{taskType}, \text{timestamp})$$

It is mathematically impossible to extract patient identities from this hash, yet any health supervisor can verify proof of care delivery.

2. **On-Chain Anti-Fraud & Replay Prevention (`AshaVault.sol`)**:
The smart contract maintains a persistent mapping:
```solidity
mapping(bytes32 => bool) public executedTasks;
```

If a duplicate or ghost entry is submitted for the same patient milestone, the contract reverts immediately with:
`"Task already recorded and rewarded"`.

3. **Autonomous Micro-Stipend Escrow**:
Upon validating task uniqueness, the contract's escrow pool executes an atomic native transfer (`0.50 $MSTC`) directly into the ASHA worker's non-custodial wallet address without human administrative bottlenecks.

---

## 2. 📱 The Frontline Clinical Mobile Application (`mobile_app/`)

The mobile client is engineered for frontline workers operating in zero-connectivity rural and semi-urban settings:

* **Offline-First Persistence**: Powered by SQLite for local household, family member, and longitudinal vitals tracking.
* **On-Device Early Warning Intelligence**:
  * **NEWS2 Scoring Engine**: Dynamically calculates National Early Warning Scores across 6 vital parameters (respiration, SpO2, systolic BP, pulse, consciousness, temperature).
  * **DELTA Trend Analysis**: Flags acute deterioration across consecutive household visits.
  * **ONNX Edge Sepsis Inference**: Executes an embedded machine learning model trained on ICU clinical time-series data to predict sepsis onset locally without network calls.
  * **Clinical Safety Override Layer**: Evaluates Shock Index ($\ge 1.0$) and quick-SOFA ($\ge 2.0$) to raise emergency flags.
* **Inclusive Accessibility**: Full multilingual interface supporting English, Hindi, Kannada, Telugu, and Tamil.
* **Local-First Media Capture**: Offline encrypted camera dropzone for prescription verification and child immunization cards.

---

## 3. 📂 Repository Organization

```text
T7-MST-Health-Vault/
├── blockchain/                  # MST Smart Contracts & Hardhat Configuration
│   ├── contracts/
│   │   └── AshaVault.sol        # Core escrow, hash anchor & stipend contract
│   ├── scripts/
│   │   └── deploy.js            # Hardhat deployment script for MST Testnet
│   ├── hardhat.config.js        # Cancun EVM network & RPC parameters
│   └── package.json
│
├── backend/                     # Web3 Relayer & Canonical Cryptographic Engine
│   ├── main.py                  # FastAPI relay broadcasting to MST node
│   ├── requirements.txt
│   └── .env.example
│
├── web_dashboard/               # Live Evaluation & Health Supervisor Portal
│   └── index.html               # Responsive portal for milestone submission & audit
│
├── mobile_app/                  # Frontline Mobile App
│   ├── lib/
│   │   ├── main.dart            # Bootstrap, SQLite, and multilingual loader
│   │   ├── services/            # NEWS2, DELTA, and ONNX Sepsis inference
│   │   └── screens/             # ASHA worker triage and household workflows
│   └── pubspec.yaml
│
├── model_pipeline/              # ML Training & ONNX Export Pipeline
│   ├── train_and_export.py      # Aggregates time-series data and exports to ONNX
│   └── smoke_test.py
│
└── README.md
```

---

## 4. 🛠️ Quickstart & Setup Guide

### Prerequisites

* Python 3.10+
* Node.js v18+ & npm
* Flutter SDK (for mobile app testing)

### Step 1: Web3 Relayer Backend

```bash
cd backend
python -m venv venv
# On Windows: venv\Scripts\activate | On Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the root:

```env
PRIVATE_KEY=your_bridgekey_private_key_here
MST_RPC_URL=https://testnetrpc.mstblockchain.com
CHAIN_ID=91562037
CONTRACT_ADDRESS=0x33Ef1680EcA40d863fc00C460EB9975bbBA12d9f
```

Run the relay server:

```bash
python -m uvicorn main:app --reload --port 8000
```

API Documentation will be live at: `http://localhost:8000/docs`.

---

### Step 2: Supervisor & Worker Web Dashboard

Simply open the client dashboard in your browser:

```bash
# Open directly in browser or launch with Live Server
open web_dashboard/index.html
```

* View live Contract Escrow balance (`10.0 $MSTC`).
* Enter patient token and milestone activity.
* Click **"Submit Record & Disburse +0.50 $MSTC"** to anchor on MST Testnet in real time.

---

### Step 3: Smart Contract Deployment (Hardhat)

```bash
cd blockchain
npm install
npx hardhat compile
npx hardhat run scripts/deploy.js --network mstTestnet
```

---

## 5. 🛡️ Verification & Anti-Fraud Demonstration

1. **Verify On-Chain Settlement**:
Inspect the deployed contract at [testnet.mstscan.com/address/0x33Ef1680EcA40d863fc00C460EB9975bbBA12d9f](https://testnet.mstscan.com/address/0x33Ef1680EcA40d863fc00C460EB9975bbBA12d9f) to review real-time `TaskAnchored` events and token transfers.

2. **Replay Rejection**:
Submitting an identical milestone for a patient token will cause the contract to revert with `"Task already recorded and rewarded"`, proving mathematical protection against ghost beneficiary claims.

---

## 👥 Team

Built with ❤️ for the **BMSCE x MST Blockchain 24-Hour Buildathon**.
