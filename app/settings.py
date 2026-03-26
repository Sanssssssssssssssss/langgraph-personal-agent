from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class StorageSettings:
    sqlite_path: str = "data/processed/personal_agent.db"
    milvus_path: str = "data/processed/personal_agent_milvus.db"
    upload_dir: str = "data/uploads"


@dataclass(frozen=True)
class RuntimeSettings:
    trace_path: str = "data/benchmarks/trace.log"


@dataclass(frozen=True)
class ConfirmationSettings:
    destructive_actions: tuple[str, ...] = ("note.delete", "remind.cancel")


@dataclass(frozen=True)
class AppSettings:
    storage: StorageSettings = field(default_factory=StorageSettings)
    runtime: RuntimeSettings = field(default_factory=RuntimeSettings)
    confirmation: ConfirmationSettings = field(default_factory=ConfirmationSettings)


def load_settings(base_dir: str | Path) -> AppSettings:
    base_dir = Path(base_dir)
    config_path = base_dir / "configs" / "settings.toml"
    if not config_path.exists():
        return AppSettings()

    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    storage = raw.get("storage", {})
    runtime = raw.get("runtime", {})
    confirmation = raw.get("confirmation", {})

    return AppSettings(
        storage=StorageSettings(
            sqlite_path=storage.get("sqlite_path", StorageSettings.sqlite_path),
            milvus_path=storage.get("milvus_path", StorageSettings.milvus_path),
            upload_dir=storage.get("upload_dir", StorageSettings.upload_dir),
        ),
        runtime=RuntimeSettings(
            trace_path=runtime.get("trace_path", RuntimeSettings.trace_path),
        ),
        confirmation=ConfirmationSettings(
            destructive_actions=tuple(
                confirmation.get(
                    "destructive_actions",
                    ConfirmationSettings.destructive_actions,
                )
            ),
        ),
    )


def resolve_path(base_dir: str | Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return Path(base_dir) / path
