"""词表引擎：从配置加载，支持增删，供策略引擎调用。"""
import json
from pathlib import Path


class WordlistEngine:
    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        self.wordlist = self._load()

    def _load(self) -> dict:
        with open(self.config_path, encoding="utf-8") as f:
            return json.load(f)

    # 提供给策略引擎的接口
    def get(self) -> dict:
        """返回整个词表（含版本）"""
        return self.wordlist

    def get_档位(self, 档位: str) -> list:
        return self.wordlist.get(档位, [])

    # 可维护能力
    def 加词(self, 档位: str, 词: str) -> str:
        if 词 not in self.wordlist[档位]:
            self.wordlist[档位].append(词)
            return f"已加入{档位}: {词}"
        return f"{词}已存在"

    def 删词(self, 档位: str, 词: str) -> str:
        if 词 in self.wordlist[档位]:
            self.wordlist[档位].remove(词)
            return f"已从{档位}移除: {词}"
        return f"{词}不存在"

    def save(self) -> None:
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.wordlist, f, ensure_ascii=False, indent=2)