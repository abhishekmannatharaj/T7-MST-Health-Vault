import os
import time
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import eth_abi
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI(title="T7 HealthVault MST Relay")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to MST Testnet
RPC_URL = os.getenv("MST_RPC_URL", "https://testnetrpc.mstblockchain.com")
w3 = Web3(Web3.HTTPProvider(RPC_URL))
try:
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
except Exception:
    pass

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
if PRIVATE_KEY:
    try:
        account = w3.eth.account.from_key(PRIVATE_KEY)
        ADMIN_ADDRESS = account.address
    except Exception:
        ADMIN_ADDRESS = None
else:
    ADMIN_ADDRESS = None

CONTRACT_ADDRESS_RAW = os.getenv("CONTRACT_ADDRESS", "0x33Ef1680EcA40d863fc00C460EB9975bbBA12d9f")
CONTRACT_ADDRESS = Web3.to_checksum_address(CONTRACT_ADDRESS_RAW) if CONTRACT_ADDRESS_RAW else None

CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "address payable", "name": "worker", "type": "address"},
            {"internalType": "bytes32", "name": "taskHash", "type": "bytes32"}
        ],
        "name": "submitAndReward",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "taskHash", "type": "bytes32"}],
        "name": "isTaskProcessed",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "workerCompletedCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI) if CONTRACT_ADDRESS else None

class RecordPayload(BaseModel):
    worker_wallet: Optional[str] = "0x7fb65d4f7aFA415d17456FaB29a4b7496a5E0257"
    worker_address: Optional[str] = None
    patient_id: Optional[str] = "ABHA-BLR-89201"
    patient_identifier: Optional[str] = None
    task_type: Optional[str] = "Maternal ANC Checkup 3"
    visit_type: Optional[str] = None
    vitals_summary: Optional[str] = "BP:120/80, HR:76, SpO2:98%"
    vitals_note: Optional[str] = None
    timestamp: Optional[int] = None

@app.get("/")
def read_root():
    return {
        "status": "T7 HealthVault Relay Online",
        "network": "MST Testnet",
        "contract": CONTRACT_ADDRESS
    }

@app.get("/api/status")
def get_status():
    try:
        is_connected = w3.is_connected()
        escrow_bal = float(w3.from_wei(w3.eth.get_balance(CONTRACT_ADDRESS), "ether")) if (CONTRACT_ADDRESS and is_connected) else 0.0
        admin_bal = float(w3.from_wei(w3.eth.get_balance(ADMIN_ADDRESS), "ether")) if (ADMIN_ADDRESS and is_connected) else 0.0
        block_num = w3.eth.block_number if is_connected else 0

        return {
            "status": "online",
            "connected": is_connected,
            "block_number": block_num,
            "contract_address": CONTRACT_ADDRESS,
            "contract_balance": f"{escrow_bal:.2f} MSTC",
            "admin_balance": f"{admin_bal:.2f} MSTC",
            "contract_balance_mstc": escrow_bal,
            "admin_balance_mstc": admin_bal
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}

def process_record(payload: RecordPayload):
    if not w3.is_connected():
        raise HTTPException(status_code=500, detail="Unable to connect to MST Testnet RPC")

    if not PRIVATE_KEY or not ADMIN_ADDRESS:
        raise HTTPException(status_code=400, detail="Admin private key not configured in .env")

    raw_worker = payload.worker_wallet or payload.worker_address or "0x7fb65d4f7aFA415d17456FaB29a4b7496a5E0257"
    try:
        worker = Web3.to_checksum_address(raw_worker)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid worker EVM wallet address format")

    patient_id = payload.patient_id or payload.patient_identifier or "ABHA-BLR-89201"
    task_type = payload.task_type or payload.visit_type or "Maternal ANC Checkup 3"
    ts = payload.timestamp or int(time.time())

    try:
        # 1. Zero-PII Canonical Keccak-256 Hash
        raw_bytes = eth_abi.encode(
            ["address", "string", "string", "uint256"],
            [worker, patient_id, task_type, ts]
        )
        task_hash = w3.keccak(raw_bytes)
    except Exception:
        # Fallback raw keccak hash if ABI encoding fails
        raw_str = f"{worker}:{patient_id}:{task_type}:{ts}".encode("utf-8")
        task_hash = w3.keccak(raw_str)

    task_hash_bytes32 = "0x" + task_hash.hex() if not isinstance(task_hash, str) else task_hash

    # 2. Duplicate Detection
    try:
        if contract.functions.isTaskProcessed(task_hash).call():
            raise HTTPException(status_code=400, detail="Task already recorded and rewarded on-chain!")
    except HTTPException:
        raise
    except Exception as e:
        if "already recorded" in str(e):
            raise HTTPException(status_code=400, detail="Task already recorded and rewarded on-chain!")

    try:
        # 3. Sign & Broadcast Transaction to MST Testnet
        nonce = w3.eth.get_transaction_count(ADMIN_ADDRESS)
        gas_price = w3.eth.gas_price

        tx = contract.functions.submitAndReward(worker, task_hash).build_transaction({
            "from": ADMIN_ADDRESS,
            "nonce": nonce,
            "gas": 250000,
            "gasPrice": gas_price,
            "chainId": 91562037
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()
        if not tx_hash_hex.startswith("0x"):
            tx_hash_hex = "0x" + tx_hash_hex

        # Wait for transaction receipt
        w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)

        worker_bal = float(w3.from_wei(w3.eth.get_balance(worker), "ether"))

        return {
            "status": "success",
            "success": True,
            "tx_hash": tx_hash_hex,
            "explorer_url": f"https://testnet.mstscan.com/tx/{tx_hash_hex}",
            "task_hash": task_hash.hex() if hasattr(task_hash, "hex") else str(task_hash),
            "worker_new_balance": float(worker_bal),
            "worker_balance_mstc": float(worker_bal)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")

@app.post("/api/submit-record")
def submit_record(payload: RecordPayload):
    return process_record(payload)

@app.post("/api/anchor-visit")
def anchor_visit(payload: RecordPayload):
    return process_record(payload)

@app.post("/api/submit-and-reward")
def submit_and_reward(payload: RecordPayload):
    return process_record(payload)
