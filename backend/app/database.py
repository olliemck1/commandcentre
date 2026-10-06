from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

# For SQLite, enable check_same_thread=False
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    """Initializes tables and ensures schema migrations are applied."""
    Base.metadata.create_all(bind=engine)
    try:
        with engine.connect() as conn:
            res = conn.execute(text("PRAGMA table_info(journal_entries)"))
            cols = [row[1] for row in res.fetchall()]
            if cols and "source" not in cols:
                conn.execute(text("ALTER TABLE journal_entries ADD COLUMN source VARCHAR(50) DEFAULT 'web'"))
                conn.commit()
    except Exception:
        pass

init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
