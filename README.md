# T7 HealthVault — Frontline Worker Zero-PII Audit & MST Blockchain Incentive Protocol

An offline-first community healthcare platform for frontline workers (ASHAs & ANMs), combining local patient vitals tracking with instant micro-stipends settled on the **MST Blockchain (Cancun EVM)**.

---

## 🔗 Live MST Testnet Verifications
- **Contract Name:** `AshaVault.sol`
- **Network:** MST Testnet (Chain ID: `91562037`)
- **Deployed Contract Address:** [`0x33Ef1680EcA40d863fc00C460EB9975bbBA12d9f`](https://testnet.mstscan.com/address/0x33Ef1680EcA40d863fc00C460EB9975bbBA12d9f)
- **Verified Transaction Hash:** [`0xdadb4ec25fc13afa95dc1f89927a181ee5c1e6eff1a06c74387fed5290d48de8`](https://testnet.mstscan.com/tx/0xdadb4ec25fc13afa95dc1f89927a181ee5c1e6eff1a06c74387fed5290d48de8)

---

## 📂 Project Architecture
- `flutter_app/`: Frontline mobile client for offline clinical vitals collection and on-device NEWS2/ONNX inference.
- `web_dashboard/`: Frontline task submission & real-time supervisor verification dashboard.
- `backend/`: FastAPI Web3 relayer computing canonical zero-PII `keccak256` digests and broadcasting to MST Testnet.
- `blockchain/`: Solidity smart contracts (`AshaVault.sol`) and Hardhat deployment configurations.

---

## 🛠️ Quickstart Guide

### 1. Web Relay Backend
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### 2. Web Dashboard
Open `web_dashboard/index.html` in your web browser.

### 3. Smart Contracts & Hardhat
```bash
cd blockchain
npm install
npx hardhat compile
npx hardhat run scripts/deploy.js --network mstTestnet
```
