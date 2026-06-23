"""
Simulated permissioned ledger (the "Blockchain Traceability" box).

A SHA-256 hash-chained, append-only ledger persisted to backend/data/ledger.json.
Each block links to the previous block's hash, so any tampering with an earlier
record breaks every subsequent hash — `verify_chain()` detects it.

This is a faithful *simulation* of a Hyperledger-Fabric-style immutable ledger,
not real Fabric infrastructure (out of scope for an offline scaffold). The
public API (add_block / get_chain / verify_chain + the smart-contract gate)
mirrors what a real chaincode integration would expose, so it is a clean
upgrade seam.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from ..config import LEDGER_PATH


def _hash_block(index: int, timestamp: str, data: dict, prev_hash: str) -> str:
    payload = json.dumps(
        {"index": index, "timestamp": timestamp, "data": data, "prev_hash": prev_hash},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _genesis() -> dict:
    ts = "2016-01-01T00:00:00+00:00"          # fixed so the genesis hash is stable
    block = {"index": 0, "timestamp": ts, "data": {"type": "genesis"}, "prev_hash": "0" * 64}
    block["hash"] = _hash_block(0, ts, block["data"], block["prev_hash"])
    return block


def _load_chain() -> list[dict]:
    if not LEDGER_PATH.exists():
        chain = [_genesis()]
        _save_chain(chain)
        return chain
    with open(LEDGER_PATH) as fh:
        return json.load(fh)


def _save_chain(chain: list[dict]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_PATH, "w") as fh:
        json.dump(chain, fh, indent=2)


# --------------------------------------------------------------------------- #
# Smart-contract validation gate
# --------------------------------------------------------------------------- #
class SmartContractError(ValueError):
    """Raised when a record violates the on-chain validation rules."""


def validate_passport(data: dict) -> None:
    """
    'Smart contract' rules enforced before a passport block is accepted.
    A real chaincode would run equivalent assertions on the peers.
    """
    if data.get("volume_kg", 0) <= 0:
        raise SmartContractError("Shipment volume must be positive.")
    if not data.get("compliance_passed", False):
        raise SmartContractError("Shipment failed destination compliance checks.")
    if not data.get("destination"):
        raise SmartContractError("Destination market is required.")


# --------------------------------------------------------------------------- #
# Public ledger API
# --------------------------------------------------------------------------- #
def add_block(data: dict) -> dict:
    """Append a validated block and return it."""
    chain = _load_chain()
    prev = chain[-1]
    index = prev["index"] + 1
    ts = _now()
    block = {
        "index": index,
        "timestamp": ts,
        "data": data,
        "prev_hash": prev["hash"],
        "hash": _hash_block(index, ts, data, prev["hash"]),
    }
    chain.append(block)
    _save_chain(chain)
    return block


def get_chain() -> list[dict]:
    return _load_chain()


def find_block(passport_id: str) -> dict | None:
    for block in _load_chain():
        if block["data"].get("passport_id") == passport_id:
            return block
    return None


def verify_chain() -> dict:
    """Recompute every hash and link; report integrity."""
    chain = _load_chain()
    for i, block in enumerate(chain):
        recomputed = _hash_block(block["index"], block["timestamp"], block["data"], block["prev_hash"])
        if recomputed != block["hash"]:
            return {"valid": False, "broken_at": i, "reason": "hash mismatch", "length": len(chain)}
        if i > 0 and block["prev_hash"] != chain[i - 1]["hash"]:
            return {"valid": False, "broken_at": i, "reason": "broken link", "length": len(chain)}
    return {"valid": True, "broken_at": None, "length": len(chain)}
