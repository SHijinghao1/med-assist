"""环境变量和配置中心"""
import os
from pathlib import Path

# ── 加载 .env ──
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(_env_path)
except ImportError:
    pass

# ── 路径 ──
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# ── 数据库 ──
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{(BASE_DIR / 'data' / 'med_assist.db').as_posix()}"
)

# 确保相对路径转为绝对路径
if "sqlite" in DATABASE_URL and ":///" in DATABASE_URL:
    _db_path = DATABASE_URL.split(":///")[-1]
    if not Path(_db_path).is_absolute():
        _abs_path = (BASE_DIR / _db_path).as_posix()
        DATABASE_URL = DATABASE_URL.replace(_db_path, _abs_path)

# ── LLM ──
LLM_PRIMARY = os.getenv("LLM_PRIMARY", "deepseek")
LLM_FALLBACK = os.getenv("LLM_FALLBACK", "qwen")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")

# ── Embedding ──
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "")

# ── Chroma ──
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(DATA_DIR / "chroma"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "med_manuals")

# ── Redis ──
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ── LangFuse ──
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:18922")
LANGFUSE_ENABLED = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)

# ── Circuit Breaker ──
CB_FAILURE_THRESHOLD = int(os.getenv("CB_FAILURE_THRESHOLD", "5"))
CB_RECOVERY_TIMEOUT = float(os.getenv("CB_RECOVERY_TIMEOUT", "30"))
CB_HALF_OPEN_PROBES = int(os.getenv("CB_HALF_OPEN_PROBES", "1"))
CB_SUCCESS_TO_CLOSE = int(os.getenv("CB_SUCCESS_TO_CLOSE", "2"))

# ── GPTCache ──
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.85"))
SEMANTIC_CACHE_TTL = int(os.getenv("SEMANTIC_CACHE_TTL", "3600"))

# ── Self-Reflection ──
REFLECTION_MAX_RETRIES = int(os.getenv("REFLECTION_MAX_RETRIES", "1"))

# ── JWT ──
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
