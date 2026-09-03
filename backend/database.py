"""
Database connection, session management, and catalog seeding for CartMind.
Uses SQLite via SQLModel per AGENTS.md and TRD.md §3.
"""

import os
from typing import Generator
from sqlmodel import SQLModel, Session, create_engine, select

from backend.models import Product

# Default database path: backend/cartmind.db
DB_FILE = os.environ.get("DATABASE_URL", "sqlite:///backend/cartmind.db")

# For SQLite, check_same_thread=False allows FastAPI multi-threading
connect_args = {"check_same_thread": False} if DB_FILE.startswith("sqlite") else {}
engine = create_engine(DB_FILE, echo=False, connect_args=connect_args)


def init_db() -> None:
    """Creates all database tables defined in SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding an isolated database session per request."""
    with Session(engine) as session:
        yield session


# Seed catalog: 15 realistic SKUs across 3 categories (PRD.md §7 FR1)
SEED_PRODUCTS = [
    # Category: Audio & Tech
    {
        "id": 1,
        "name": "Apex Wireless ANC Headphones",
        "price": 12499.0,
        "stock_qty": 25,
        "margin_pct": 45.0,
        "category": "Audio & Tech",
        "description": "Flagship over-ear active noise-canceling headphones with 40-hour battery and spatial audio.",
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80",
    },
    {
        "id": 2,
        "name": "StudioPro USB Condenser Mic",
        "price": 4999.0,
        "stock_qty": 15,
        "margin_pct": 40.0,
        "category": "Audio & Tech",
        "description": "Cardioid condenser microphone with studio-grade 24-bit/192kHz resolution and gain knob.",
        "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&q=80",
    },
    {
        "id": 3,
        "name": "SonicPulse Waterproof Speaker",
        "price": 2799.0,
        "stock_qty": 30,
        "margin_pct": 50.0,
        "category": "Audio & Tech",
        "description": "Rugged IPX7 portable Bluetooth speaker with deep 360-degree punchy bass and 15h playtime.",
        "image_url": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&q=80",
    },
    {
        "id": 4,
        "name": "AuraNoise True Wireless Earbuds",
        "price": 3499.0,
        "stock_qty": 20,
        "margin_pct": 38.0,
        "category": "Audio & Tech",
        "description": "Ergonomic TWS earbuds with hybrid ANC, transparency mode, and ultra low-latency gaming mode.",
        "image_url": "https://images.unsplash.com/photo-1572536147248-ac59a8abfa4b?w=600&q=80",
    },

    # Category: Everyday Carry
    {
        "id": 5,
        "name": "Nomad Canvas Commuter Backpack",
        "price": 3999.0,
        "stock_qty": 18,
        "margin_pct": 55.0,
        "category": "Everyday Carry",
        "description": "Weather-resistant waxed canvas pack with dedicated 16-inch laptop compartment and luggage pass-through.",
        "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&q=80",
    },
    {
        "id": 6,
        "name": "TitanFold Titanium Slim Wallet",
        "price": 1499.0,
        "stock_qty": 40,
        "margin_pct": 65.0,
        "category": "Everyday Carry",
        "description": "Aerospace-grade titanium cardholder with RFID blocking, expandable cavity, and cash strap.",
        "image_url": "https://images.unsplash.com/photo-1627123424574-724758594e93?w=600&q=80",
    },
    {
        "id": 7,
        "name": "HydroChamber Insulated Bottle 750ml",
        "price": 999.0,
        "stock_qty": 50,
        "margin_pct": 50.0,
        "category": "Everyday Carry",
        "description": "Double-walled vacuum insulated stainless steel bottle keeping drinks icy cold for 24h or hot for 12h.",
        "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&q=80",
    },
    {
        "id": 8,
        "name": "Chronos Minimalist Chronograph",
        "price": 6499.0,
        "stock_qty": 12,
        "margin_pct": 42.0,
        "category": "Everyday Carry",
        "description": "Sapphire crystal Japanese quartz chronograph with quick-release Italian calfskin leather strap.",
        "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&q=80",
    },
    {
        "id": 9,
        "name": "ProShield Braided USB-C Cable (2m)",
        "price": 799.0,
        "stock_qty": 60,
        "margin_pct": 60.0,
        "category": "Everyday Carry",
        "description": "Ultra-durable Kevlar-reinforced 100W PD nylon braided charging and high-speed data cable.",
        "image_url": "https://images.unsplash.com/photo-1541689592655-f5f52825a3b8?w=600&q=80",
    },

    # Category: Desk & Workspace
    {
        "id": 10,
        "name": "UltraSpeed USB-C 100W Hub",
        "price": 3499.0,
        "stock_qty": 2,  # Intentionally low stock (2 units) for Phase 6 failure injection scenario
        "margin_pct": 25.0,
        "category": "Desk & Workspace",
        "description": "7-in-1 multi-port aluminum hub with dual 4K HDMI, Gigabit Ethernet, SD card, and 100W PD.",
        "image_url": "https://images.unsplash.com/photo-1544652478-6653e09f18a2?w=600&q=80",
    },
    {
        "id": 11,
        "name": "MagStand 3-in-1 Wireless Charger",
        "price": 2199.0,
        "stock_qty": 15,
        "margin_pct": 35.0,
        "category": "Desk & Workspace",
        "description": "Fast magnetic floating charging stand for phone, smartwatch, and wireless earbuds simultaneously.",
        "image_url": "https://images.unsplash.com/photo-1586816879360-004f5b0c51e3?w=600&q=80",
    },
    {
        "id": 12,
        "name": "ErgoLift Aluminum Laptop Riser",
        "price": 1899.0,
        "stock_qty": 22,
        "margin_pct": 48.0,
        "category": "Desk & Workspace",
        "description": "Foldable ergonomic aluminum stand with optimized heat dissipation ventilation for 11-17 inch laptops.",
        "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=600&q=80",
    },
    {
        "id": 13,
        "name": "PrecisionDesk Wool Felt Desk Mat",
        "price": 1299.0,
        "stock_qty": 35,
        "margin_pct": 52.0,
        "category": "Desk & Workspace",
        "description": "Premium water-resistant Merino wool felt mat with anti-fray stitched edges and non-slip natural rubber backing.",
        "image_url": "https://images.unsplash.com/photo-1581291518857-4e27b48ff24e?w=600&q=80",
    },
    {
        "id": 14,
        "name": "Lumina Arc Smart Monitor Lightbar",
        "price": 2999.0,
        "stock_qty": 14,
        "margin_pct": 32.0,
        "category": "Desk & Workspace",
        "description": "Asymmetric glare-free monitor lamp with wireless desktop rotary dial and auto-dimming ambient light sensor.",
        "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&q=80",
    },
    {
        "id": 15,
        "name": "KeyCraft Compact Mechanical Keyboard",
        "price": 5499.0,
        "stock_qty": 10,
        "margin_pct": 28.0,
        "category": "Desk & Workspace",
        "description": "Hot-swappable 75% mechanical keyboard with factory-lubed linear switches, sound dampening, and RGB.",
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&q=80",
    },
]


def seed_catalog(db: Session = None) -> None:
    """Seeds the catalog with the initial 15 SKUs if empty."""
    def _seed(s: Session):
        existing_count = len(s.exec(select(Product)).all())
        if existing_count == 0:
            for item in SEED_PRODUCTS:
                p = Product(**item)
                s.add(p)
            s.commit()

    if db is not None:
        _seed(db)
    else:
        with Session(engine) as session:
            _seed(session)
