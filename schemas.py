"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

# Skema untuk transaksi keuangan asrama
class Transaction(BaseModel):
    tanggal: datetime = Field(..., description="Tanggal transaksi")
    penghuni: Optional[str] = Field(None, description="Nama penghuni (opsional)")
    kamar: Optional[str] = Field(None, description="Nomor kamar (opsional)")
    keterangan: str = Field(..., description="Deskripsi transaksi")
    jumlah: float = Field(..., ge=0, description="Jumlah uang (Rupiah)")
    tipe: Literal["pemasukan", "pengeluaran"] = Field(..., description="Jenis transaksi")

# Contoh lain (tidak digunakan saat ini)
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")
