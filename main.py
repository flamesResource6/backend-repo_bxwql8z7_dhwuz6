import os
from datetime import datetime
from typing import List, Optional, Literal

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import db, create_document, get_documents
from schemas import Transaction as TransactionSchema

app = FastAPI(title="Dormitory Finance API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Models ----------
class TransactionIn(BaseModel):
    tanggal: datetime = Field(..., description="Tanggal transaksi")
    penghuni: Optional[str] = Field(None, description="Nama penghuni")
    kamar: Optional[str] = Field(None, description="Nomor kamar")
    keterangan: str = Field(..., description="Deskripsi transaksi")
    jumlah: float = Field(..., ge=0, description="Jumlah rupiah")
    tipe: Literal["pemasukan", "pengeluaran"]


class TransactionOut(TransactionIn):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------- Helpers ----------
COLLECTION = "transaction"  # schemas.Transaction -> collection name = lowercase class name


def is_admin(token: Optional[str]) -> bool:
    admin_token = os.getenv("ADMIN_TOKEN")
    return bool(admin_token) and token == admin_token


# ---------- Routes ----------
@app.get("/")
def read_root():
    return {"message": "Backend Keuangan Asrama aktif"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


@app.get("/api/transactions")
def list_transactions(
    limit: int = Query(100, ge=1, le=500),
    tipe: Optional[str] = Query(None, pattern="^(pemasukan|pengeluaran)$"),
):
    filt = {}
    if tipe:
        filt["tipe"] = tipe
    docs = get_documents(COLLECTION, filt, limit)
    # Sort by tanggal desc, fallback to created_at
    def sort_key(d):
        return d.get("tanggal") or d.get("created_at") or datetime.min

    docs_sorted = sorted(docs, key=sort_key, reverse=True)
    # Normalize output
    result: List[TransactionOut] = []
    for d in docs_sorted:
        d["id"] = str(d.get("_id"))
        d.pop("_id", None)
        result.append(d)  # FastAPI auto-serializes
    return {"items": result}


@app.get("/api/stats")
def stats():
    docs = get_documents(COLLECTION, {}, None)
    pemasukan = sum(d.get("jumlah", 0) for d in docs if d.get("tipe") == "pemasukan")
    pengeluaran = sum(d.get("jumlah", 0) for d in docs if d.get("tipe") == "pengeluaran")
    saldo = pemasukan - pengeluaran
    return {"pemasukan": pemasukan, "pengeluaran": pengeluaran, "saldo": saldo}


@app.post("/api/transactions", status_code=201)
def create_transaction(tx: TransactionIn, x_admin_token: Optional[str] = Header(None)):
    if not is_admin(x_admin_token):
        raise HTTPException(status_code=403, detail="Hanya admin yang boleh mengedit")

    # Validate using schema class (optional, we already have TransactionIn)
    _ = TransactionSchema(**tx.model_dump())
    new_id = create_document(COLLECTION, tx)
    return {"id": new_id, "message": "Transaksi berhasil ditambahkan"}


@app.delete("/api/transactions/{tx_id}")
def delete_transaction(tx_id: str, x_admin_token: Optional[str] = Header(None)):
    if not is_admin(x_admin_token):
        raise HTTPException(status_code=403, detail="Hanya admin yang boleh mengedit")
    if db is None:
        raise HTTPException(status_code=500, detail="Database tidak tersedia")
    res = db[COLLECTION].delete_one({"_id": __import__("bson").ObjectId(tx_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    return {"message": "Transaksi dihapus"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
